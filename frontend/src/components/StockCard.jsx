// 종목 하나의 최신 예측 결과를 보여주는 카드.
// 디자인은 아직 확정 전이라 기능(데이터 표시)만 충실히 구현한 상태.
export default function StockCard({ prediction }) {
  const {
    name, code, market,
    current_close, predicted_close,
    direction, change, target_date,
  } = prediction

  const directionClass =
    direction === '상승' ? 'up' : direction === '하락' ? 'down' : 'flat'

  return (
    <div className="stock-card">
      <h3>
        {name} <span className="code">({code})</span>
      </h3>
      <p className="market">{market}</p>
      <p>현재가: {current_close.toLocaleString()}</p>
      <p>
        예측가 ({target_date}): {predicted_close.toLocaleString()}
      </p>
      <p className={directionClass}>
        {direction} ({change > 0 ? '+' : ''}
        {change.toLocaleString()})
      </p>
    </div>
  )
}
