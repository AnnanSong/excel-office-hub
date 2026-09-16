import { useState } from 'react'
import { apiClient, downloadFromUrl } from '../../api/client'

export default function CreateSheetsPage() {
  const [names, setNames] = useState('')
  const [headers, setHeaders] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const nameList = names.split(/\n|,/).map((s) => s.trim()).filter(Boolean)
    if (nameList.length === 0) {
      setMessage('请至少填写一个工作表名称')
      return
    }

    setLoading(true)
    setMessage('')
    const formData = new FormData()
    formData.append('names', nameList.join('\n'))
    if (headers.trim()) formData.append('headers', headers)

    try {
      const res = await apiClient.post('/api/create-sheets/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const url = res.data.download_url
      if (url) {
        downloadFromUrl(url, 'created_sheets.xlsx')
        setMessage(res.data.message || '创建完成')
      } else {
        setMessage('未返回下载链接')
      }
    } catch (err: any) {
      setMessage(err.response?.data?.detail || err.message || '请求失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900">批量创建指定名称工作表</h2>
      <p className="mt-1 text-sm text-gray-600">按名称列表快速生成包含多个工作表的 Excel 文件。</p>

      <form onSubmit={handleSubmit} className="mt-6 card space-y-5">
        <div>
          <label className="label">工作表名称</label>
          <textarea
            value={names}
            onChange={(e) => setNames(e.target.value)}
            rows={6}
            placeholder={`1月\n2月\n3月\n一季度汇总`}
            className="input"
            required
          />
          <p className="mt-1 text-xs text-gray-500">每行一个名称，也支持逗号分隔</p>
        </div>

        <div>
          <label className="label">默认表头（可选）</label>
          <textarea
            value={headers}
            onChange={(e) => setHeaders(e.target.value)}
            rows={3}
            placeholder={`日期\n项目\n金额`}
            className="input"
          />
          <p className="mt-1 text-xs text-gray-500">每行一个表头列名，会写入每个工作表的第一行</p>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? '处理中...' : '创建并下载'}
        </button>

        {message && (
          <div className={`rounded-md p-3 text-sm ${message.includes('失败') || message.includes('请') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {message}
          </div>
        )}
      </form>
    </div>
  )
}
