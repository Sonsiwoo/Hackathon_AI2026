// 백엔드(FastAPI) /api/predictions 엔드포인트 호출 함수 모음.
// vite.config.js의 proxy 설정 덕분에 개발 중에는 그냥 '/api/...' 상대경로로 호출하면
// vite 개발 서버가 알아서 http://localhost:8000 으로 전달해준다.

const API_BASE = '/api/predictions'

export async function fetchLatestPredictions() {
  const res = await fetch(`${API_BASE}/latest`)
  if (!res.ok) {
    throw new Error('예측 데이터를 불러오지 못했습니다.')
  }
  return res.json()
}

export async function fetchPredictionHistory(code) {
  const res = await fetch(`${API_BASE}/${code}`)
  if (!res.ok) {
    throw new Error('예측 히스토리를 불러오지 못했습니다.')
  }
  return res.json()
}
