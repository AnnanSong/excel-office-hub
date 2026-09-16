import axios from 'axios'

// 前端调用的后端地址：
// - 本地开发：走 vite 代理的相对路径 /api
// - GitHub Pages 部署：构建时通过 VITE_API_BASE 注入后端(Render)完整地址
const baseURL = import.meta.env.VITE_API_BASE || '/api'

export const apiClient = axios.create({
  baseURL,
  timeout: 120000,
  headers: {
    'Accept': 'application/json',
  },
})

export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
  download_url?: string
}

export function downloadFromUrl(url: string, filename: string) {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
