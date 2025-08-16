
import Layout from '../components/Layout'
import Link from 'next/link'

export default function Home() {
  return (
    <Layout>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card">
          <div className="font-semibold mb-2">EDINET</div>
          <p className="text-sm text-gray-300 mb-3">企業を検索し、書類種類（docType）をトグルで選択して一覧・解析。</p>
          <Link href="/edinet" className="button-primary inline-block">EDINETページへ</Link>
        </div>
        <div className="card">
          <div className="font-semibold mb-2">J-Quants</div>
          <p className="text-sm text-gray-300 mb-3">財務データ比較・可視化・シナリオ分析。</p>
          <Link href="/jquants" className="button-primary inline-block">J-Quantsページへ</Link>
        </div>
      </div>
    </Layout>
  )
}
