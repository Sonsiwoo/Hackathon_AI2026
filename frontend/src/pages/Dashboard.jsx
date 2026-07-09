import { useEffect, useState } from 'react'
import { fetchLatestPredictions } from '../api/predictions.js'
import StockCard from '../components/StockCard.jsx'

// 메인 화면: 종목별 최신 예측을 카드 그리드로 보여준다.
export default function Dashboard() {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchLatestPredictions()
      .then(setPredictions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>불러오는 중...</p>
  if (error) return <p>에러: {error}</p>
  if (predictions.length === 0) return <p>아직 저장된 예측 데이터가 없습니다.</p>

  return (
    <div className="dashboard">
      <h1>Top 5 종목 주가 예측</h1>
      <div className="card-grid">
        {predictions.map((p) => (
          <StockCard key={p.code} prediction={p} />
        ))}
      </div>
    </div>
  )
}
