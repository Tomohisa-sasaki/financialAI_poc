import type { NextApiRequest, NextApiResponse } from 'next'

export const config = { api: { bodyParser: true } }

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ error: 'Method Not Allowed' })
  }

  const base = process.env.BACKEND_API_BASE_URL || 'http://localhost:8000'
  const user = process.env.API_USER || 'admin'
  const pass = process.env.API_PASSWORD || 'password123'
  const auth = 'Basic ' + Buffer.from(`${user}:${pass}`).toString('base64')

  const idem = req.headers['x-idempotency-key']
  const headers: