import Dashboard from './pages/Dashboard.jsx'

// 지금은 대시보드 한 페이지뿐이라 라우터 없이 바로 렌더링.
// 나중에 종목 상세 페이지 등이 추가되면 react-router 도입을 고려하면 됨.
export default function App() {
  return <Dashboard />
}
