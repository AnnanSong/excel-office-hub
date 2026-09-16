import { useState } from 'react'
import { apiClient, downloadFromUrl } from '../../api/client'

export default function AggregatePage() {
  const [files, setFiles] = useState<FileList | null>(null)
  const [keyColumns, setKeyColumns] = useState('')
  const [requiredColumns, setRequiredColumns] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!files || files.length === 0) {
      setMessage('请至少上传一个文件')
      return
    }

    setLoading(true)
    setMessage('')
    const formData = new FormData()
    Array.from(files).forEach((f) => formData.append('files', f))
    if (keyColumns) formData.append('key_columns', JSON.stringify(keyColumns.split(/[,，]/).map((s) => s.trim()).filter(Boolean)))
    if (requiredColumns) formData.append('required_columns', JSON.stringify(requiredColumns.split(/[,，]/).map((s) => s.trim()).filter(Boolean)))

    try {
      const res = await apiClient.post('/api/aggregate/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const url = res.data.download_url
      if (url) {
        downloadFromUrl(url, 'aggregate_result.xlsx')
        setMessage(res.data.message || '汇总完成')
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
      <h2 className="text-2xl font-bold text-gray-900">多文件汇总</h2>
      <p className="mt-1 text-sm text-gray-600">纵向堆叠多个 Excel，自动去重并生成异常表。</p>

      <form onSubmit={handleSubmit} className="mt-6 card space-y-5">
        <div>
          <label className="label">上传多个 Excel</label>
          <input
            type="file"
            multiple
            accept=".xlsx,.xls,.xlsm"
            onChange={(e) => setFiles(e.target.files)}
            className="input py-1.5"
          />
        </div>

        <div>
          <label className="label">业务主键（去重用，可选）</label>
          <input
            type="text"
            value={keyColumns}
            onChange={(e) => setKeyColumns(e.target.value)}
            placeholder="例如：工号，多个用逗号分隔"
            className="input"
          />
        </div>

        <div>
          <label className="label">必填字段（缺失会进入异常表，可选）</label>
          <input
            type="text"
            value={requiredColumns}
            onChange={(e) => setRequiredColumns(e.target.value)}
            placeholder="例如：工号,姓名,部门"
            className="input"
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? '处理中...' : '开始汇总'}
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
