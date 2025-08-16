
import Layout from '../../components/Layout'
import { useState } from 'react'

export default function AIPage() {
  const [q, setQ] = useState('今後3年の利益成長の見通しを比較してください')
  const [ans, setAns] = useState('')
  const ask = async () => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    const user = process.env.API_USER || 'admin'
    const pass = process.env.API_PASSWORD || 'password123'
    const auth = 'Basic ' + btoa(`${user}:${pass}`)
    const r = await fetch(`${base}/ai/ask`, { method: 'POST', headers: { Authorization: auth, 'Content-Type': 'application/json'}, body: JSON.stringify({ question: q }) })
    const j = await r.json(); setAns(j.answer || '(no answer)')
  }
  return (
    <Layout>
      <div className="card space-y-3 max-w-3xl">
        <div className="font-semibold">AI 要約/QA</div>
        <textarea value={q} onChange={e=>setQ(e.target.value)} rows={4} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2" />
        <button onClick={ask} className="button-primary">質問する</button>
        {ans && <div className="text-sm text-gray-200 whitespace-pre-wrap">{ans}</div>}
      </div>
    </Layout>
  )
}
