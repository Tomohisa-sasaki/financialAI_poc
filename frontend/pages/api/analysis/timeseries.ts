import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET')
    return res.status(405).json({ error: 'Method Not Allowed' })
  }

  const q = (req.query.q as string || '').trim()
  const limit = Number(req.query.limit ?? 20) || 20
  if (!q) return res.status(400).json({ error: 'Missing query parameter: q' })

  const base = process.env.BACKEND_API_BASE_URL || 'http://localhost:8000'
  const user = process.env.API_USER || 'admin'
  const pass = process.env.API_PASSWORD || 'password123'
  const auth = 'Basic ' + Buffer.from(`${user}:${pass}`).toString('base64')

  const url = `${base}/companies/search?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(String(limit))}`
  try {
    const r = await fetch(url, { headers: { Authorization: auth } })
    const text = await r.text()
    if (!r.ok) {
      let detail: any
      try { detail = JSON.parse(text) } catch { detail = { 