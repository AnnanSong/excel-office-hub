import { useState } from 'react'
import { apiClient, downloadFromUrl } from '../../api/client'

function splitList(v: string): string[] {
  return v.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
}

export default function ComparePage() {
  const [oldFile, setOldFile] = useState<File | null>(null)
  const [newFile, setNewFile] = useState<File | null>(null)
  const [keyColumns, setKeyColumns] = useState('')
  const [compareColumns, setCompareColumns] = useState('')
  const [headerRow, setHeaderRow] = useState(1)
  const [ignoreWhitespace, setIgnoreWhitespace] = useState(true)
  const [ignoreCase, setIgnoreCase] = useState(false)
  const [tolerance, setTolerance] = useState('0')
  const [outputMode, setOutputMode] = useState<'summary' | 'full'>('summary')
  const [includeUnchanged, setIncludeUnchanged] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [ok, setOk] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!oldFile || !newFile) {
      setMessage('请同时上传旧版和新版文件')
      setOk(false)
      return
    }
    if (!keyColumns.trim()) {
      setMessage('请填写关键字段（用于匹配两版记录）')
      setOk(false)
      return
    }

    setLoading(true)
    setMessage('')
    const fd = new FormData()
    fd.append('old_file', oldFile)
    fd.append('new_file', newFile)
    fd.append('key_columns', JSON.stringify(splitList(keyColumns)))
    if (compareColumns.trim()) fd.append('compare_columns', JSON.stringify(splitList(compareColumns)))
    fd.append('header_row', String(headerRow))
    fd.append('ignore_whitespace', String(ignoreWhitespace))
    fd.append('ignore_case', String(ignoreCase))
    fd.append('numeric_tolerance', tolerance || '0')
    fd.append('output_mode', outputMode)
    fd.append('include_unchanged', String(includeUnchanged))

    try {
      const res = await apiClient.post('/api/compare/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const url = res.data.download_url
      if (url) {
        downloadFromUrl(url, 'compare_result.xlsx')
        setMessage(res.data.message || '比对完成')
        setOk(true)
      } else {
        setMessage('未返回下载链接')
        setOk(false)
      }
    } catch (err: any) {
      setMessage(err.response?.data?.detail || err.message || '请求失败')
      setOk(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900">数据比对</h2>
      <p className="mt-1 text-sm text-gray-600">
        按关键字段匹配旧版与新版，自动识别新增、删除、修改并高亮差异。
      </p>

      <form onSubmit={handleSubmit} className="mt-6 card space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">旧版文件（原版）</label>
            <input type="file" accept=".xlsx,.xls,.xlsm"
              onChange={(e) => setOldFile(e.target.files?.[0] || null)} className="input py-1.5" />
          </div>
          <div>
            <label className="label">新版文件（最新版）</label>
            <input type="file" accept=".xlsx,.xls,.xlsm"
              onChange={(e) => setNewFile(e.target.files?.[0] || null)} className="input py-1.5" />
          </div>
        </div>

        <div>
          <label className="label">关键字段（用于匹配两版记录，必填）</label>
          <input type="text" value={keyColumns} onChange={(e) => setKeyColumns(e.target.value)}
            placeholder="例如：往来单位  或组合：部门,项目编号" className="input" required />
          <p className="mt-1 text-xs text-gray-500">按此字段匹配，行顺序变化不影响比对结果</p>
        </div>

        <div>
          <label className="label">比对字段（留空则比对除关键字段外全部）</label>
          <input type="text" value={compareColumns} onChange={(e) => setCompareColumns(e.target.value)}
            placeholder="例如：期初,本期增加,本期减少,期末" className="input" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">表头所在行</label>
            <input type="number" min={1} value={headerRow}
              onChange={(e) => setHeaderRow(Number(e.target.value) || 1)} className="input" />
          </div>
          <div>
            <label className="label">数值容差（≤此差值视为相等）</label>
            <input type="number" step="0.01" min={0} value={tolerance}
              onChange={(e) => setTolerance(e.target.value)} className="input" />
          </div>
        </div>

        <div>
          <label className="label">输出模式</label>
          <select value={outputMode} onChange={(e) => setOutputMode(e.target.value as any)} className="input">
            <option value="summary">仅输出差异（汇总 + 新增/删除/修改明细）</option>
            <option value="full">差异 + 并排全量对比表</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={ignoreWhitespace} onChange={(e) => setIgnoreWhitespace(e.target.checked)} />
            比较时忽略首尾空格
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={ignoreCase} onChange={(e) => setIgnoreCase(e.target.checked)} />
            比较时忽略大小写
          </label>
          {outputMode === 'full' && (
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={includeUnchanged} onChange={(e) => setIncludeUnchanged(e.target.checked)} />
              并排对比中包含未变化记录
            </label>
          )}
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? '处理中...' : '开始比对'}
        </button>

        {message && (
          <div className={`rounded-md p-3 text-sm ${ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {message}
          </div>
        )}
      </form>
    </div>
  )
}
