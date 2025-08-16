import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET')
    return res.status(405).json({ error: 'Method Not Allowed' })
  }
  const { date, start, end, edinet_code, doc_type_codes } = req.query
  const base = process.env.BACKEND_API_BASE_URL || 'http://localhost:8000'
  const user = process.env.API_USER || 'admin'
  const pass = process.env.API_PASSWORD || 'password123'
  const auth = 'Basic ' + Buffer.from(`${user}:${pass}`).toString('base64')

  const params = new URLSearchParams()
  if (typeof date === 'string' && date) params.set('date', date)
  if (typeof start === 'string' && start) params.set('start', start)
  if (typeof end === 'string' && end) params.set('end', end)
  if (typeof edinet_code === 'string' && edinet_code) params.set('edinet_code', edinet_code)
  if (typeof doc_type_codes === 'string' && doc_type_codes) params.set('doc_type_codes', doc_type_codes)

  try {
    const r = await fetch(`${base}/edinet/list?${params.toString()}`, { headers: { Authorization: auth } })
    const text = await r.text()
    let data: any
    try { data = JSON.parse(text) } catch { data = { detail: text } }
    res.setHeader('Cache-Control', 's-maxage=30, stale-while-revalidate=120')
    return res.status(r.status).json(data)
  } catch (e: any) {
    return res.status(502).json({ error: 'Bad Gateway', detail: e?.message || String(e) })
  }
}
