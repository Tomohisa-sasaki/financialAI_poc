import Layout from '../components/Layout'
import CompanyPicker from '../components/CompanyPicker'
import ChartCard from '../components/ChartCard'
import PDFButton from '../components/PDFButton'
import EmailSend from '../components/EmailSend'
import { useEffect, useMemo, useState } from 'react'

const DOC_TYPES = [
  { code: '120', label: '有価証券報告書' },
  { code: '130', label: '四半期報告書' },
  { code: '140', label: '臨時報告書' },
  { code: '150', label: '訂正報告書' },
  { code: '160', label: '内部統制報告書' },
]

const DATE_RX = /^\d{4}-\d{2}-\d{2}$/
const validDate = (s: string) => DATE_RX.test(s)
const validRange = (s: string, e: string) => validDate(s) && validDate(e) && new Date(s) <= new Date(e)

// Types
interface FilingRow { docID: string; submitter: string; title: string; date: string }

type Mode = 'day' | 'range'

type SortKey = 'docID' | 'submitter' | 'title' | 'date'

type SortDir = 'asc' | 'desc'

type Row = { x: string; value: number }

type Candidate = { label: string; patterns: string[] }

export default function EDINETPage() {
  const [companyIds, setCompanyIds] = useState<string[]>([])
  const [edinetCode, setEdinetCode] = useState<string>('')
  const [mode, setMode] = useState<Mode>('day')
  const [date, setDate] = useState<string>('')
  const [start, setStart] = useState<string>('')
  const [end, setEnd] = useState<string>('')
  const [docTypes, setDocTypes] = useState<string[]>(['120','130'])
  const [filings, setFilings] = useState<any[]>([])
  const [parsed, setParsed] = useState<any|null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState<number>(1)
  const pageSize = 20
  const [parsingId, setParsingId] = useState<string>('')

  // ---------- Helpers for parsed visualization ----------
  const norm = (s: string) => s.toLowerCase().replace(/[\s_\-‐・:：/\\]/g, '')
  const toNumber = (v: any): number | null => {
    if (v == null) return null
    if (typeof v === 'number' && isFinite(v)) return v
    if (typeof v === 'string') {
      const n = parseFloat(v.replace(/[,\\s]/g, ''))
      return isNaN(n) ? null : n
    }
    if (typeof v === 'object') {
      const entries = Object.entries(v).filter(([_, val]) => typeof val === 'number' || (typeof val === 'string' && !isNaN(parseFloat((val as string).replace(/[,\\s]/g, '')))))
      if (entries.length === 0) return null
      const sorted = entries.sort(([ka], [kb]) => String(ka).localeCompare(String(kb)))
      const last = sorted[sorted.length - 1][1]
      return toNumber(last)
    }
    return null
  }
  const pickValue = (obj: any, patterns: string[]): number | null => {
    if (!obj || typeof obj !== 'object') return null
    for (const [k, v] of Object.entries(obj)) {
      const nk = norm(String(k))
      if (patterns.some(p => nk.includes(norm(p)))) {
        const n = toNumber(v)
        if (n != null) return n
      }
    }
    return null
  }
  const makeRows = (section: any, candidates: Candidate[]): Row[] => {
    if (!section) return []
    const rows: Row[] = []
    for (const c of candidates) {
      const val = pickValue(section, c.patterns)
      if (val != null) rows.push({ x: c.label, value: val })
    }
    return rows
  }

  const PL_CANDS: Candidate[] = [
    { label: '売上高', patterns: ['売上高','売上','営業収益','revenue','sales'] },
    { label: '営業利益', patterns: ['営業利益','operating income','operating profit'] },
    { label: '当期純利益', patterns: ['当期純利益','純利益','net income','profit attributable','当期利益'] },
  ]
  const BS_CANDS: Candidate[] = [
    { label: '総資産', patterns: ['総資産','total assets'] },
    { label: '純資産', patterns: ['純資産','net assets','equity','株主資本'] },
    { label: '自己資本比率(%)', patterns: ['自己資本比率','equity ratio'] },
  ]
  const CF_CANDS: Candidate[] = [
    { label: '営業CF', patterns: ['営業活動によるキャッシュフロー','営業cf','cash flows from operating','cfo'] },
    { label: '投資CF', patterns: ['投資活動によるキャッシュフロー','投資cf','cash flows from investing','cfi'] },
    { label: '財務CF', patterns: ['財務活動によるキャッシュフロー','財務cf','cash flows from financing','cff'] },
  ]

  const plRows = useMemo(() => makeRows(parsed?.PL, PL_CANDS), [parsed])
  const bsRows = useMemo(() => makeRows(parsed?.BS, BS_CANDS), [parsed])
  const cfRows = useMemo(() => makeRows(parsed?.CF, CF_CANDS), [parsed])

  // ------------------------------------------------------

  useEffect(() => {
    const resolve = async () => {
      if (companyIds.length === 0) return
      try {
        const r = await fetch(`/api/companies/search?q=${encodeURIComponent(companyIds[0])}`)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const list = await r.json()
        const hit = Array.isArray(list) ? list.find((x: any) => x.id === companyIds[0]) : null
        if (hit && hit.edinet_code) setEdinetCode(hit.edinet_code)
      } catch (e:any) { /* ignore */ }
    }
    resolve()
  }, [companyIds])

  const canList = useMemo(() => {
    if (!edinetCode) return false
    if (mode === 'day') return validDate(date)
    return validRange(start, end)
  }, [edinetCode, mode, date, start, end])

  const listFilings = async () => {
    if (!canList || loading) return
    setLoading(true); setError(''); setParsed(null); setPage(1)
    const params = new URLSearchParams()
    if (edinetCode) params.set('edinet_code', edinetCode)
    if (mode === 'day' && validDate(date)) params.set('date', date)
    if (mode === 'range' && validRange(start, end)) { params.set('start', start); params.set('end', end) }
    if (docTypes.length > 0) params.set('doc_type_codes', docTypes.join(','))
    try {
      const r = await fetch(`/api/edinet/list?${params.toString()}`)
      const j = await r.json()
      if (!r.ok) throw new Error(j?.detail || `HTTP ${r.status}`)
      setFilings(j.filings || [])
    } catch (e:any) {
      setError(e?.message || '一覧取得に失敗しました'); setFilings([])
    } finally { setLoading(false) }
  }

  const parseDoc = async (docId: string) => {
    setLoading(true); setError(''); setParsingId(docId)
    try {
      const r = await fetch(`/api/edinet/parse?document_id=${encodeURIComponent(docId)}`)
      const j = await r.json()
      if (!r.ok) throw new Error(j?.detail || `HTTP ${r.status}`)
      setParsed(j.parsed || null)
    } catch (e:any) {
      setError(e?.message || '解析に失敗しました'); setParsed(null)
    } finally { setLoading(false); setParsingId('') }
  }

  const rows: FilingRow[] = useMemo(() => {
    return (filings || []).map((f: any) => ({
      docID: String(f.docID || f.docId || ''),
      submitter: String(f.filerName || f.submitterName || '-'),
      title: String(f.docDescription || f.title || '-'),
      date: String(f.submitDateTime || f.docSubmitDateTime || ''),
    }))
  }, [filings])

  const sortedRows = useMemo(() => {
    const key = sortKey
    const cmp = (a: FilingRow, b: FilingRow) => {
      let va: any = a[key] as any
      let vb: any = b[key] as any
      if (key === 'date') { va = new Date(a.date).getTime(); vb = new Date(b.date).getTime() }
      else { va = String(va).toLowerCase(); vb = String(vb).toLowerCase() }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    }
    return [...rows].sort(cmp)
  }, [rows, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize))
  const pagedRows = useMemo(() => sortedRows.slice((page-1)*pageSize, page*pageSize), [sortedRows, page])

  const toggleSort = (k: keyof FilingRow) => {
    if (sortKey === k) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(k as SortKey); setSortDir('asc') }
  }

  const ariaSort = (k: SortKey) => sortKey !== k ? 'none' : (sortDir === 'asc' ? 'ascending' : 'descending')
  const sortIcon = (k: SortKey) => sortKey !== k ? '↕' : (sortDir === 'asc' ? '↑' : '↓')

  return (
    <Layout>
      <div className="space-y-6">
        <div className="card space-y-3">
          <div className="font-semibold">EDINET 検索</div>
          <div className="text-sm text-gray-300">企業名をドラッグで選択 → EDINETコードを自動解決。docTypeは下のトグルで選択。</div>
          <CompanyPicker onChange={setCompanyIds} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <label className="text-sm">EDINETコード
              <input value={edinetCode} onChange={e=>setEdinetCode(e.target.value)} placeholder="E01730 など" className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2" />
            </label>
            <div className="text-sm">
              <div className="mb-1">対象期間</div>
              <div className="flex gap-4 items-center">
                <label className="flex items-center gap-1"><input type="radio" checked={mode==='day'} onChange={()=>{setMode('day'); setStart(''); setEnd('')}}/> 単日</label>
                <label className="flex items-center gap-1"><input type="radio" checked={mode==='range'} onChange={()=>{setMode('range'); setDate('')}}/> 期間</label>
              </div>
            </div>
            <div />
          </div>

          {mode === 'day' ? (
            <label className="text-sm block">日付（単日）
              <input value={date} onChange={e=>setDate(e.target.value)} placeholder="YYYY-MM-DD" className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2" />
              {!validDate(date) && date && <div className="text-xs text-red-400">YYYY-MM-DD 形式で入力してください</div>}
            </label>
          ) : (
            <div className="text-sm grid grid-cols-2 gap-2">
              <label>開始
                <input value={start} onChange={e=>setStart(e.target.value)} placeholder="YYYY-MM-DD" className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2" />
                {!validDate(start) && start && <div className="text-xs text-red-400">YYYY-MM-DD</div>}
              </label>
              <label>終了
                <input value={end} onChange={e=>setEnd(e.target.value)} placeholder="YYYY-MM-DD" className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2" />
                {!validDate(end) && end && <div className="text-xs text-red-400">YYYY-MM-DD</div>}
                {mode==='range' && start && end && !validRange(start,end) && <div className="text-xs text-red-400">開始日は終了日以前である必要があります</div>}
              </label>
            </div>
          )}

          <div className="text-sm">
            <div className="mb-1">docType（書類種別）</div>
            <div className="flex flex-wrap gap-2">
              {DOC_TYPES.map(d => (
                <button
                  key={d.code}
                  onClick={()=>setDocTypes(prev => prev.includes(d.code) ? prev.filter(c=>c!==d.code) : [...prev, d.code])}
                  aria-pressed={docTypes.includes(d.code)}
                  className={`px-3 py-1 rounded border ${docTypes.includes(d.code)?'bg-brand-700/30 border-brand-700 text-brand-300':'bg-gray-900 border-gray-700'}`}
                >
                  {d.label} ({d.code})
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button disabled={!canList || loading} onClick={listFilings} className={`button-primary ${(!canList || loading) ? 'opacity-50 cursor-not-allowed' : ''}`}>{loading ? '取得中...' : '一覧を取得'}</button>
            {error && <span className="text-xs text-red-400">{error}</span>}
          </div>
        </div>

        <div className="card">
          <div className="font-semibold mb-2">書類一覧 {rows.length ? `(${rows.length}件)` : ''}</div>
          {rows.length === 0 ? <div className="text-sm text-gray-400">該当なし</div> :
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-300">
                  <th className="py-2 pr-3 cursor-pointer" onClick={() => toggleSort('docID')} aria-sort={ariaSort('docID') as any}>docID <span className="text-xs">{sortIcon('docID')}</span></th>
                  <th className="py-2 pr-3 cursor-pointer" onClick={() => toggleSort('submitter')} aria-sort={ariaSort('submitter') as any}>提出者 <span className="text-xs">{sortIcon('submitter')}</span></th>
                  <th className="py-2 pr-3 cursor-pointer" onClick={() => toggleSort('title')} aria-sort={ariaSort('title') as any}>書類名 <span className="text-xs">{sortIcon('title')}</span></th>
                  <th className="py-2 pr-3 cursor-pointer" onClick={() => toggleSort('date')} aria-sort={ariaSort('date') as any}>提出日 <span className="text-xs">{sortIcon('date')}</span></th>
                  <th className="py-2 pr-3"></th>
                </tr>
              </thead>
              <tbody>
                {pagedRows.map((f, i) => (
                  <tr key={`${f.docID}-${i}`} className="border-t border-gray-800">
                    <td className="py-2 pr-3">{f.docID}</td>
                    <td className="py-2 pr-3">{f.submitter}</td>
                    <td className="py-2 pr-3">{f.title}</td>
                    <td className="py-2 pr-3">{f.date}</td>
                    <td className="py-2 pr-3"><button onClick={()=>parseDoc(f.docID)} disabled={!!parsingId} className="text-brand-300 hover:underline disabled:opacity-50">{parsingId===f.docID?'解析中...':'解析'}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-end gap-3 mt-3 text-sm">
              <button className="px-2 py-1 border border-gray-700 rounded disabled:opacity-50" onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page<=1}>前へ</button>
              <div>{(page-1)*pageSize+1} - {Math.min(page*pageSize, sortedRows.length)} / {sortedRows.length}</div>
              <button className="px-2 py-1 border border-gray-700 rounded disabled:opacity-50" onClick={()=>setPage(p=>Math.min(totalPages,p+1))} disabled={page>=totalPages}>次へ</button>
            </div>
          </div>}
        </div>

        {parsed && (
          <>
            <div className="card space-y-3 chart-capture">
              <div className="font-semibold">解析結果（JSON）</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div><div className="font-medium mb-1">PL</div><pre className="bg-gray-900 text-xs p-2 rounded border border-gray-800 overflow-auto">{JSON.stringify(parsed.PL || {}, null, 2)}</pre></div>
                <div><div className="font-medium mb-1">BS</div><pre className="bg-gray-900 text-xs p-2 rounded border border-gray-800 overflow-auto">{JSON.stringify(parsed.BS || {}, null, 2)}</pre></div>
                <div><div className="font-medium mb-1">CF</div><pre className="bg-gray-900 text-xs p-2 rounded border border-gray-800 overflow-auto">{JSON.stringify(parsed.CF || {}, null, 2)}</pre></div>
              </div>
            </div>

            {(plRows.length>0 || bsRows.length>0 || cfRows.length>0) && (
              <div className="card space-y-4">
                <div className="font-semibold">主要KPIグラフ</div>
                {plRows.length>0 && (
                  <div className="chart-capture"><ChartCard title="PL 主要項目" data={plRows} keys={["value"]} /></div>
                )}
                {bsRows.length>0 && (
                  <div className="chart-capture"><ChartCard title="BS 主要項目" data={bsRows} keys={["value"]} /></div>
                )}
                {cfRows.length>0 && (
                  <div className="chart-capture"><ChartCard title="CF 主要項目" data={cfRows} keys={["value"]} /></div>
                )}
              </div>
            )}

            <div className="card space-y-3">
              <div className="font-semibold">エクスポート</div>
              <div className="flex flex-wrap gap-3 items-center">
                <PDFButton title="EDINET解析レポート" />
              </div>
              <EmailSend />
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}