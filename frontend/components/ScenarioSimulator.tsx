
import { useState } from 'react'
export default function ScenarioSimulator({ companies }: { companies: string[] }) {
  const [company, setCompany] = useState(companies[0] || '')
  const [growth, setGrowth] = useState(0)
  const [gm, setGm] = useState(40)
  const [sga, setSga] = useState(10)
  const [result, setResult] = useState<string>('')
  const apply = () => {
    const baseROE = 10
    const projected = baseROE * (1 + growth/100) * (gm/40) * (10/max(1,sga))
    setResult(`Projected ROE: ${projected.toFixed(2)}%`)
  }
  return (
    <div className="card space-y-2">
      <div className="font-semibold">シナリオモデリング</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <label className="text-sm">会社
          <select value={company} onChange={e=>setCompany(e.target.value)} className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2">
            {companies.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="text-sm">売上成長率(%)<input type="number" value={growth} onChange={e=>setGrowth(parseFloat(e.target.value))} className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2" /></label>
        <label className="text-sm">粗利率(%)<input type="number" value={gm} onChange={e=>setGm(parseFloat(e.target.value))} className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2" /></label>
        <label className="text-sm">販管費率(%)<input type="number" value={sga} onChange={e=>setSga(parseFloat(e.target.value))} className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2" /></label>
      </div>
      <div><button onClick={apply} className="button-primary">適用</button></div>
      {result && <div className="text-brand-300">{result}</div>}
    </div>
  )
}
