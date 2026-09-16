import { useState } from 'react'
import { apiClient, downloadFromUrl } from '../../api/client'

function splitList(v: string): string[] {
  return v.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
}

export default function SplitPage() {
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'by_column' | 'by_row_count' | 'by_sheet'>('by_column')
  const [columns, setColumns] = useState('')
  const [columnSeparator, setColumnSeparator] = useState('_')
  const [rowCount, setRowCount] = useState('100')
  const [namingTemplate, setNamingTemplate] = useState('{value}')
  const [headerRow, setHeaderRow] = useState(1)
  const [skipEmpty, setSkipEmpty] = useState(true)
  const [preserveFormat, setPreserveFormat] = useState(true)
  const [preserveMerged, setPreserveMerged] = useState(true)
  const [freezeHeader, setFreezeHeader] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [ok, setOk] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setMessage('请先上传文件')
      setOk(false)
      return
    }
    if (mode === 'by_column' && !columns.trim()) {
      setMessage('请填写拆分列')
      setOk(false)
      return
    }

    setLoading(true)
    setMessage('')
    const fd = new FormData()
    fd.append('file', file)
    fd.append('mode', mode)
    if (mode === 'by_column') {
      fd.append('columns', JSON.stringify(splitList(columns)))
      fd.append('column_separator', columnSeparator || '_')
    }
    if (mode === 'by_row_count') fd.append('row_count', rowCount)
    fd.append('naming_template', namingTemplate)
    fd.append('header_row', String(headerRow))
    fd.append('skip_empty', String(skipEmpty))
    fd.append('preserve_format', String(preserveFormat))
    fd.append('preserve_merged', String(preserveMerged))
    fd.append('freeze_header', String(freezeHeader))

    try {
      const res = await apiClient.post('/api/split/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const url = res.data.download_url
      if (url) {
        downloadFromUrl(url, 'split_result.zip')
        setMessage(res.data.message || '拆分完成')
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
      <h2 className="text-2xl font-bold text-gray-900">智能拆分</h2>
      <p className="mt-1 text-sm text-gray-600">
        按列（支持多列组合）、按行数或按工作表拆分，可保留原表格式。
      </p>

      <form onSubmit={handleSubmit} className="mt-6 card space-y-5">
        <div>
          <label className="label">上传 Excel</label>
          <input type="file" accept=".xlsx,.xls,.xlsm"
            onChange={(e) => setFile(e.target.files?.[0] || null)} className="input py-1.5" />
        </div>

        <div>
          <label className="label">拆分模式</label>
          <select value={mode} onChange={(e) => setMode(e.target.value as typeof mode)} className="input">
            <option value="by_column">按列分组（支持多列组合）</option>
            <option value="by_row_count">按行数切块</option>
            <option value="by_sheet">按工作表拆分</option>
          </select>
        </div>

        {mode === 'by_column' && (
          <>
            <div>
              <label className="label">拆分列（多列用逗号分隔，可组合）</label>
              <input type="text" value={columns} onChange={(e) => setColumns(e.target.value)}
                placeholder="例如：部门  或组合：部门,岗位,职级"
                className="input" required />
              <p className="mt-1 text-xs text-gray-500">
                支持列名，也支持 Excel 列字母（如 L,AD,H）。多列组合时会按组合值分组，如「研发部_工程师」
              </p>
            </div>
            <div>
              <label className="label">多列连接符</label>
              <input type="text" value={columnSeparator} onChange={(e) => setColumnSeparator(e.target.value)}
                placeholder="_" className="input" />
            </div>
          </>
        )}

        {mode === 'by_row_count' && (
          <div>
            <label className="label">每个文件行数（不含表头）</label>
            <input type="number" min={1} value={rowCount}
              onChange={(e) => setRowCount(e.target.value)} className="input" required />
          </div>
        )}

        <div>
          <label className="label">输出文件名模板</label>
          <input type="text" value={namingTemplate}
            onChange={(e) => setNamingTemplate(e.target.value)}
            placeholder="{value}_{count}笔" className="input" />
          <p className="mt-1 text-xs text-gray-500">
            占位符：{'{value}'} 分组值、{'{count}'} 笔数、{'{index}'} 序号、{'{sheet}'} 源表名。
            例：<code className="bg-gray-100 px-1 rounded">{'{value}_{count}笔'}</code> → 研发部_工程师_2笔.xlsx
          </p>
        </div>

        <div>
          <label className="label">表头所在行</label>
          <input type="number" min={1} value={headerRow}
            onChange={(e) => setHeaderRow(Number(e.target.value) || 1)} className="input" />
          <p className="mt-1 text-xs text-gray-400">很多模板表头在第 3 行</p>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={preserveFormat} onChange={(e) => setPreserveFormat(e.target.checked)} />
            保留原表格式（字体 / 边框 / 底色 / 列宽）
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={preserveMerged} disabled={!preserveFormat}
              onChange={(e) => setPreserveMerged(e.target.checked)} />
            保留合并单元格
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={freezeHeader} onChange={(e) => setFreezeHeader(e.target.checked)} />
            冻结表头行
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={skipEmpty} onChange={(e) => setSkipEmpty(e.target.checked)} />
            跳过分组键为空的行
          </label>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? '处理中...' : '开始拆分'}
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
