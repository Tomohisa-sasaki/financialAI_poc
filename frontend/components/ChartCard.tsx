
import { ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, Line, BarChart, Bar } from 'recharts'
const palette = ['#10b981', '#84cc16', '#22d3ee', '#a3e635', '#facc15']

const isPercentKey = (k: string) => /roe|roa|margin|ratio|growth/i.test(k)
const fmtNum = (v: number) => {
  if (v == null || isNaN(v)) return ''
  const abs = Math.abs(v)
  return abs >= 1000 ? Math.round(v).toLocaleString() : (Math.round(v * 100) / 100).toString()
}
const fmtPct = (v: number) => (v == null || isNaN(v)) ? '' : `${(v * 100).toFixed(1)}%`

export default function ChartCard({ title, data, kind='line', keys }: { title: string, data: any[], kind?: 'line'|'bar', keys: string[] }) {
  const percentKeys = keys.filter(isPercentKey)
  const valueKeys = keys.filter(k => !isPercentKey(k))
  const hasBoth = percentKeys.length > 0 && valueKeys.length > 0

  const renderLines = () => (
    keys.map((k, i) => (
      <Line key={k} type="monotone" dataKey={k} stroke={palette[i%palette.length]} strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 5 }} yAxisId={isPercentKey(k) && hasBoth ? 'right' : 'left'} />
    ))
  )
  const renderBars = () => (
    keys.map((k, i) => (
      <Bar key={k} dataKey={k} fill={palette[i%palette.length]} yAxisId={isPercentKey(k) && hasBoth ? 'right' : 'left'} />
    ))
  )

  return (
    <div className="card">
      <div className="mb-2 font-semibold">{title}</div>
      <div className="h-80 chart-capture">
        <ResponsiveContainer width="100%" height="100%">
          {kind === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis dataKey="x" stroke="#cbd5e1" tick={{ fill: '#cbd5e1' }} />
              <YAxis yAxisId="left" stroke="#cbd5e1" tick={{ fill: '#cbd5e1' }} tickFormatter={v => f