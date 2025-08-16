
import Link from 'next/link'
import { ReactNode } from 'react'
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="font-bold text-lg">Financial AI</div>
          <nav className="space-x-4 text-sm">
            <Link className="hover:text-brand-300" href="/">Home</Link>
            <Link className="hover:text-brand-300" href="/jquants">J-Quants</Link>
            <Link className="hover:text-brand-300" href="/edinet">EDINET</Link>
            <Link className="hover:text-brand-300" href="/ai">AI</Link>
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
    </div>
  )
}
