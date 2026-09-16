import { useState } from 'react'
import { apiClient, downloadFromUrl } from '../../api/client'

function splitList(v: string): string[] {
  return v.split(/[,，\n]/).map((s) => s.trim()).filter(Boolean)
}

export default function MergePage() {
  const [files, setFiles] = useState<FileList | null>(null)
  const [template, setTemplate] = useState<File | null>(null)

  const [mergeMode, setMergeMode] = useState<'sheets' | 'files'>('sheets')
  const [sheetMatch, setSheetMatch] = useState<'normalize' | 'exact'>('normalize')
  const [headerRow, setHeaderRow] = useState(1)
  const [skipSpacers, setSkipSpacers] = useState(true)
  const [addLog, setAddLog] = useState(true)
  const [keyColumns, setKeyColumns] = useState('')
  const [requiredColumns, setRequiredColumns] = useState('')
  const [expectedSheets, setExpectedSheets] = useState('')
  const [fieldMap, setFieldMap] = useState('')

  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [ok, setOk] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!files || files.length === 0) {
      setMessage('请至少上传一个文件')
      setOk(false)
      return
    }
    if (fieldMap.trim()) {
      try {
        JSON.parse(fieldMap)
      } catch {
        setMessage('字段映射不是合法 JSON，例如 {"姓名":"员工姓名"}')
        setOk(false)
        return
      }
    }

    setLoading(true)
    setMessage('')
    const fd = new FormData()
    Array.from(files).forEach((f) => fd.append('files', f))
    if (template) fd.append('template', template)
    fd.append('merge_mode', mergeMode)
    fd.append('sheet_match', sheetMatch)
    fd.append('header_row', String(headerRow))
    fd.append('skip_spacers', String(skipSpacers))
    fd.append('add_log', String(addLog))
    if (keyColumns) fd.append('key_columns', JSON.stringify(splitList(keyColumns)))
    if (requiredColumns) fd.append('required_columns', JSON.stringify(splitList(requiredColumns)))
    if (expectedSheets) fd.append('expected_sheets', JSON.stringify(splitList(expectedSheets)))
    if (fieldMap.trim()) fd.append('field_map', fieldMap)

    try {
      const res = await apiClient.post('/api/merge/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const url = res.data.download_url
      if (url) {
        downloadFromUrl(url, 'merge_result.xlsx')
        setMessage(res.data.message || '汇总完成')
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
    <div className="max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900">多 Sheet 合并汇总</h2>
      <p className="mt-1 text-sm text-gray-600">
        遍历每个文件的全部工作表，按归一化后的名称分组分别汇总，自动去重、检测缺失并生成导入日志。
      </p>

      <form onSubmit={handleSubmit} className="mt-6 card space-y-6">
        <div>
          <label className="label">上传多个 Excel（各公司/各人回传）</label>
          <input
            type="file"
            multiple
            accept=".xlsx,.xls,.xlsm"
            onChange={(e) => setFiles(e.target.files)}
            className="input py-1.5"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">汇总模式</label>
            <select value={mergeMode} onChange={(e) => setMergeMode(e.target.value as any)} className="input">
              <option value="sheets">按 Sheet 分组（主表-明细分别汇总）</option>
              <option value="files">每文件取一个 Sheet（旧行为）</option>
            </select>
          </div>
          <div>
            <label className="label">Sheet 名匹配</label>
            <select value={sheetMatch} onChange={(e) => setSheetMatch(e.target.value as any)} className="input">
              <option value="normalize">归一化匹配（去序号/期间/统一横杠）</option>
              <option value="exact">严格匹配</option>
            </select>
          </div>
          <div>
            <label className="label">表头所在行</label>
            <input
              type="number"
              min={1}
              value={headerRow}
              onChange={(e) => setHeaderRow(Number(e.target.value) || 1)}
              className="input"
            />
            <p className="mt-1 text-xs text-gray-400">很多模板表头在第 3 行</p>
          </div>
          <div className="flex flex-col justify-end gap-2 pb-1">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={skipSpacers} onChange={(e) => setSkipSpacers(e.target.checked)} />
              跳过占位页（&gt;&gt;&gt; / 黄色标签）
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={addLog} onChange={(e) => setAddLog(e.target.checked)} />
              生成导入日志
            </label>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">业务主键（跨文件去重，可选）</label>
            <input type="text" value={keyColumns} onChange={(e) => setKeyColumns(e.target.value)}
              placeholder="例如：工号" className="input" />
          </div>
          <div>
            <label className="label">必填字段（缺失进异常表，可选）</label>
            <input type="text" value={requiredColumns} onChange={(e) => setRequiredColumns(e.target.value)}
              placeholder="例如：工号,姓名,部门" className="input" />
          </div>
          <div>
            <label className="label">期望 Sheet（缺失会标红，可选）</label>
            <textarea value={expectedSheets} onChange={(e) => setExpectedSheets(e.target.value)}
              placeholder="工资明细&#10;研发费用&#10;社保明细" rows={3} className="input" />
          </div>
          <div>
            <label className="label">字段映射（JSON，可选）</label>
            <textarea value={fieldMap} onChange={(e) => setFieldMap(e.target.value)}
              placeholder='{"姓名":"员工姓名","金额":"应发合计"}' rows={3} className="input font-mono text-xs" />
          </div>
        </div>

        <div>
          <label className="label">汇总模板（可选，上传后按模板 Sheet 填入并保留格式）</label>
          <input type="file" accept=".xlsx,.xls,.xlsm"
            onChange={(e) => setTemplate(e.target.files?.[0] || null)} className="input py-1.5" />
          <p className="mt-1 text-xs text-gray-400">提供模板后，结果将基于模板生成；模板中无对应数据的 Sheet 会被标红提示</p>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? '处理中...' : '开始合并汇总'}
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
