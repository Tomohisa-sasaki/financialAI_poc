import type { NextApiRequest, NextApiResponse } from 'next'

// Upstream expects JSON body; we return a PDF on success
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

  // Forward optional idempotency for safe retries
  const idem = req.headers['x-idempotency-key']
  const headers: Record<string, string> = { Authorization: auth, 'Content-Type': 'application/json' }
  if (idem) headers['X-Idempotency-Key'] = Array.isArray(idem) ? idem[0] : String(idem)

  try {
    const r = await fetch(`${base}/report/pdf`, {
      method: 'POST',
      headers,
      body: JSON.stringify(req.body || {}),
    })

    const disp = r.headers.get('content-disposition') || 'attachment; filename="report.pdf"'
    const ct = r.headers.get('content-type') || 'application/pdf'

    // If upstream returned an error, surface it as JSON (don't send bogus PDF headers)
    if (!r.ok) {
      const text = await r.text()
      let detail: any
      try { detail = JSON.parse(text) } catch { detail = { detail: text } }
      return res.status(r.status).json({ error: 'Upstream error', ...detail })
    }

    // Success: pass through headers and binary body
    const arrayBuf = await r.arrayBuffer()
    res.setHeader('Content-Type', ct)
    res.setHeader('Content-Disposition', disp)
    // Avoid caching potentially sensitive PDFs at the edge
    res.setHeader('Cache-Control', 'private, no-store')
    return res.status(200).send(Buffer.from(arrayBuf))
  } catch (e: any) {
    return res.status(502).json({ error: 'Bad Gateway', detail: e?.message || String(e) })
  }
}
