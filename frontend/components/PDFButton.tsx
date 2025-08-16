import { useState } from 'react'

type CaptureImage = { dataUrl: string; width: number; height: number }

type Props = {
  title?: string
  apiPath?: string
  selector?: string
  className?: string
  filenameFallback?: string
}

const DEFAULT_SELECTOR = '.chart-capture'

async function capture(selector: string): Promise<CaptureImage[]> {
  if (typeof window === 'undefined') return []
  const { default: html2canvas } = await import('html2canvas')
  const nodes = Array.from(document.querySelectorAll(selector)) as HTMLElement[]
  const scale = Math.min(3, (window.devicePixelRatio || 1) * 2)
  const images: CaptureImage[] = []
  for (const el of nodes) {
    const canvas = await html2canvas(el, { scale })
    images.push({ dataUrl: canvas.toDataURL('image/png'), width: canvas.width, height: canvas.height })
  }
  return images
}

function parseFilenameFromContentDisposition(h?: string | null): string | null {
  if (!h) return null
  const m1 = /filename\*=UTF-8''([^;]+)/i.exec(h)
  if (m1) return decodeURIComponent(m1[1])
  const m2 = /filename="?([^\";]+)"?/i.exec(h)
  if (m2) return m2[1]
  return null
}

export default function PDFButton({
  title = 'EDINET解析レポート',
  apiPath = '/api/report/pdf',
  selector = DEFAULT_SELECTOR,
  className = '',
  filenameFallback = 'report.pdf',
}: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  const onClick = async () => {
    if (loading) return
    setLoading(true); setError('')
    try {
      const images = await capture(selector)
      const idem =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`
      const r = await fetch(apiPath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Idempotency-Key': idem },
        body: JSON.stringify({ title, images }),
      })
      if (!r.ok) {
        const text = await r.text()
        let detail: any
        try { detail = JSON.parse(text) } catch { detail = { detail: text } }
        throw new Error(detail?.detail || detail?.error || `HTTP ${r.status}`)
      }
      const disp = r.headers.get('content-disposition')
      const filename = parseFilenameFromContentDisposition(disp) || filenameFallback
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setError(e?.message || 'PDF生成に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={className}>
      <button onClick={onClick} disabled={loading} aria-busy={loading} className={`button-primary ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}>
        {loading ? 'PDF生成中…' : 'PDFダウンロード'}
      </button>
      {error && <div className="text-xs text-red-400 mt-1">{error}</div>}
      <div className="text-xs text-gray-400 mt-1">※ 画面内の <code>.chart-capture</code> 要素を画像化してPDFにまとめます。</div>
    </div>
  )
}