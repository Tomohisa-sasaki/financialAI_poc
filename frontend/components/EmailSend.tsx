import { useState } from 'react'

type CaptureImage = { dataUrl: string; width: number; height: number }

type Props = {
  defaultTo?: string
  apiPath?: string
  selector?: string
  className?: string
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

export default function EmailSend({
  defaultTo = '',
  apiPath = '/api/report/email',
  selector = DEFAULT_SELECTOR,
  className = '',
}: Props) {
  const [to, setTo] = useState<string>(defaultTo)
  const [subject, setSubject] = useState<string>('EDINET解析レポート')
  const [message, setMessage] = useState<string>('解析結果を送付します。')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState(false)

  const validEmail = (s: string) => /.+@.+\..+/.test(s)

  const onSend = async () => {
    if (loading || !validEmail(to)) return
    setLoading(true); setError(''); setOk(false)
    try {
      const images = await capture(selector)
      const idem =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`
      const r = await fetch(apiPath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Idempotency-Key': idem },
        body: JSON.stringify({ to, subject, message, images }),
      })
      const text = await r.text()
      if (!r.ok) {
        let detail: any
        try { detail = JSON.parse(text) } catch { detail = { detail: text } }
        throw new Error(detail?.detail || detail?.error || `HTTP ${r.status}`)
      }
      setOk(true)
    } catch (e: any) {
      setError(e?.mes