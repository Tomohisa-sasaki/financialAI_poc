import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET')
    return res.status(405).json({ error: 'Method Not Allowed' })
  }
  const document_id = (req.query.document_id as string || '').trim()
  if (!document_id) return res.status(400).json({ error: 'Missing query parameter: document_id' })

  const base = process.env.BACKEND_API_BASE_URL || 'http://localhost:8000'
  const user = process.env.API_USER || 'admin'
  const pass = process.env.API_PASSWORD || 'password123'
  const auth = 'Basic ' + Buffer.from(`${user}:${pass}`).toString('base64')

  try {
    const r = await fetch(`${base}/edinet/parse?document_id=${encodeURIComponent(document_id)}`, { headers: { Authorization: auth } })
    const text = await r.text()
    let data: any
    try { data = JSON.parse(text) } catch { data = { detail: text } }
    res.setHeader('Cache-Control', 's-maxage=30, stale-while-revalidate=120')
    return res.status(r.status).json(data)
  } catch (e: any) {
    return res.status(502).json({ error: 'Bad Gateway', detail: e?.message || String(e) })
  }
}
