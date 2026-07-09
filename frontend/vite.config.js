import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 서버(vite)가 /api로 오는 요청을 백엔드(FastAPI, 8000번 포트)로 그대로 전달해준다.
// 이렇게 하면 프론트엔드 코드에서 항상 상대경로 '/api/...'만 쓰면 되고,
// CORS나 백엔드 주소를 코드에 하드코딩할 필요가 없다.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
