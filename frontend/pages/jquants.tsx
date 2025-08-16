import Layout from '../components/Layout'
import CompanyPicker from '../components/CompanyPicker'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts'
// （必要なら PDF/メールも）
import PDFButton from '../components/PDFButton'
import EmailSend from '../components/EmailSend'

type Freq = 'A' | 'Q' // Annual / Quarterly

type IndicatorCode =
  | 'revenue'
  | 'operating_income'
  | 'net_income'
  | 'eps'
  | 'roe'
  | 'roa'
  | 'op_margin'
  | 'free_cf'

const INDICATORS: { code: IndicatorCode; label: string; unit?: string }[] = [
  { code: 'revenue',          label: '売上高' },
  { code: 'operating_income', label: '営業利益' },
  { code: 'net_income',       label: '当期純利益' },
  { code: 'eps',              label: 'EPS' },
  { code: 'roe',              label: 'ROE(%)', unit: '%' },
  { code: 'roa',              label: 'ROA(%)', unit: '%' },
  { code: 'op_margin',        label: '営業利益率(%)', unit: '%' },
  { code: 'free_cf',          label: 'フリーCF' },
]

type FlatPoint = { x: string; value: number; company: string; indicator: IndicatorCode }

// ユーティリティ
const fmtNum = (n?: number, unit?: string) => {
  if (n == null || !isFinite(n)) return '-'
  const abs = Math.abs(n)
  const sign = n < 0 ? '-' : ''
  if (abs >= 1_000_000_000_000) return `${sign}${(abs / 1_000_000_000_000).toFixed(2)}兆${unit ?? ''}`
  if (abs >= 100_000_000)       return `${sign}${(abs / 100_000_000).toFixed(2)}億${unit ?? ''}`
  if (abs >= 10_000)           return `${sign}${(abs / 10_000).toFixed(2)}万${unit ?? ''}`
  return `${sign}${abs.toLocaleString()}${unit ?? ''}`
}

const COLORS = [
  '#34d399', '#60a5fa', '#f472b6', '#f59e0b', '#a78bfa',
  '#22d3ee', '#fb7185', '#84cc16', '#e879f9', '#4ade80',
]

// Recharts Tooltip
function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded border border-gray-700 bg-gray-900 px-3 py-2 text-xs">
      <div className="font-semibold mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded" style={{ background: p.color }} />
          <span>{p.name}: {fmtNum(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ---- メイン ----
export default function JQuantsPage() {
  // 選択
  const [companyIds, setCompanyIds] = useState<string[]>([])
  const [freq, setFreq] = useState<Freq>('A')
  const thisYear = new Date().getFullYear()
