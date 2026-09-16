import { useState } from 'react'
import { apiClient, downloadFromUrl } from '../../api/client'

type RuleType = 'required' | 'type' | 'range' | 'enum' | 'pattern' | 'compare' | 'threshold'

interface RuleRow {
  id: number
  column: string
  rule_type: RuleType
  level: 'error' | 'warning'
  min: string
  max: string
  value_type: 'number' | 'date' | 'text'
  allowed: string
  pattern: string
  compare_columns: string
  compare_op: string
  signs: string
  baseline_column: string
  threshold_type: 'abs' | 'pct_change' | 'ratio'
  message: string
}

let idSeq = 1
const newRule = (): RuleRow => ({
  id: idSeq++,
  column: '',
  rule_type: 'required',
  level: 'error',
  min: '',
  max: '',
  value_type: 'number',
  allowed: '',
  pattern: '',
  compare_columns: '',
  compare_op: 'eq',
  signs: '',
  baseline_column: '',
  threshold_type: 'abs',
  message: '',
})

const RULE_LABELS: Record<RuleType, string> = {
  required: '必填（非空）',
  type: '类型（数字/日期）',
  range: '范围（数值区间）',
  enum: '枚举（允许值）',
  pattern: '正则匹配',
  compare: '列间勾稽',
  threshold: '阈值告警',
}

function buildRulePayload(r: RuleRow, idx: number): Record<string, unknown> {
  const base: Record<string, unknown> = {
    rule_id: `R${String(idx + 1).padStart(3, '0')}`,
    rule_type: r.rule_type,
    level: r.level,
    message: r.message || undefined,
  }
  if (r.rule_type !== 'compare') base.column = r.column
  if (r.rule_type === 'type') base.value_type = r.value_type
  if (r.rule_type === 'range') {
    if (r.min) base.min = Number(r.min)
    if (r.max) base.max = Number(r.max)
    base.allow_negative = !(r.min && Number(r.min) >= 0)
  }
  if (r.rule_type === 'enum') base.allowed = r.allowed.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  if (r.rule_type === 'pattern') base.pattern = r.pattern
  if (r.rule_type === 'compare') {
    base.compare_columns = r.compare_columns.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
    base.compare_op = r.compare_op
    if (r.compare_op === 'sum_eq' && r.signs.trim()) {
      base.signs = r.signs.split(/[,，]/).map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n))
    }
    base.tolerance = 0.01
  }
  if (r.rule_type === 'threshold') {
    base.threshold_type = r.threshold_type
    if (r.max) base.max = Number(r.max)
    if (r.baseline_column) base.baseline_column = r.baseline_column
  }
  return base
}

export default function ValidatePage() {
  const [file, setFile] = useState<File | null>(null)
  const [headerRow, setHeaderRow] = useState(1)
  const [rules, setRules] = useState<RuleRow[]>([newRule()])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [ok, setOk] = useState(false)

  const update = (id: number, patch: Partial<RuleRow>) =>
    setRules((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setMessage('请先上传 Excel 文件')
      setOk(false)
      return
    }
    const valid = rules.filter((r) => (r.rule_type === 'compare' ? r.compare_columns.trim() : r.column.trim()))
    if (valid.length === 0) {
      setMessage('请至少配置一条有效规则（填写作用列）')
      setOk(false)
      return
    }

    setLoading(true)
    setMessage('')
    const fd = new FormData()
    fd.append('file', file)
    fd.append('header_row', String(headerRow))
    fd.append('rules', JSON.stringify(valid.map((r, i) => buildRulePayload(r, i))))

    try {
      const res = await apiClient.post('/api/validate/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const url = res.data.download_url
      if (url) {
        downloadFromUrl(url, 'validate_report.xlsx')
        setMessage(res.data.message || '校验完成')
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
      <h2 className="text-2xl font-bold text-gray-900">数据校验</h2>
      <p className="mt-1 text-sm text-gray-600">
        配置校验规则，一键检查必填、类型、范围、枚举、格式与勾稽，输出校验报告。
      </p>

      <form onSubmit={handleSubmit} className="mt-6 card space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">上传 Excel</label>
            <input type="file" accept=".xlsx,.xls,.xlsm"
              onChange={(e) => setFile(e.target.files?.[0] || null)} className="input py-1.5" />
          </div>
          <div>
            <label className="label">表头所在行</label>
            <input type="number" min={1} value={headerRow}
              onChange={(e) => setHeaderRow(Number(e.target.value) || 1)} className="input" />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className="label mb-0">校验规则</label>
            <button type="button" onClick={() => setRules((rs) => [...rs, newRule()])}
              className="text-sm text-excel-600 font-medium hover:underline">+ 添加规则</button>
          </div>

          <div className="mt-3 space-y-3">
            {rules.map((r) => (
              <div key={r.id} className="rounded-lg border border-gray-200 p-3 space-y-2">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <select value={r.rule_type} onChange={(e) => update(r.id, { rule_type: e.target.value as RuleType })}
                    className="input">
                    {Object.entries(RULE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                  {r.rule_type !== 'compare' && (
                    <input type="text" value={r.column} onChange={(e) => update(r.id, { column: e.target.value })}
                      placeholder="作用列，如：金额" className="input" />
                  )}
                  <select value={r.level} onChange={(e) => update(r.id, { level: e.target.value as any })} className="input">
                    <option value="error">错误（阻断）</option>
                    <option value="warning">警告</option>
                  </select>
                </div>

                {r.rule_type === 'type' && (
                  <select value={r.value_type} onChange={(e) => update(r.id, { value_type: e.target.value as any })}
                    className="input">
                    <option value="number">数字</option>
                    <option value="date">日期</option>
                    <option value="text">文本</option>
                  </select>
                )}

                {r.rule_type === 'range' && (
                  <div className="grid grid-cols-2 gap-2">
                    <input type="number" value={r.min} onChange={(e) => update(r.id, { min: e.target.value })}
                      placeholder="最小值（可空）" className="input" />
                    <input type="number" value={r.max} onChange={(e) => update(r.id, { max: e.target.value })}
                      placeholder="最大值（可空）" className="input" />
                  </div>
                )}

                {r.rule_type === 'enum' && (
                  <input type="text" value={r.allowed} onChange={(e) => update(r.id, { allowed: e.target.value })}
                    placeholder="允许值，逗号分隔：已审核,待审核" className="input" />
                )}

                {r.rule_type === 'pattern' && (
                  <input type="text" value={r.pattern} onChange={(e) => update(r.id, { pattern: e.target.value })}
                    placeholder="正则，如：^P\d{3}$" className="input font-mono text-xs" />
                )}

                {r.rule_type === 'compare' && (
                  <div className="space-y-2">
                    <input type="text" value={r.compare_columns}
                      onChange={(e) => update(r.id, { compare_columns: e.target.value })}
                      placeholder="参与列，逗号分隔：期末,期初,本期增加,本期减少" className="input" />
                    <div className="grid grid-cols-2 gap-2">
                      <select value={r.compare_op} onChange={(e) => update(r.id, { compare_op: e.target.value })}
                        className="input">
                        <option value="eq">等于 (=)</option>
                        <option value="ne">不等于 (≠)</option>
                        <option value="gt">大于 (&gt;)</option>
                        <option value="lt">小于 (&lt;)</option>
                        <option value="gte">大于等于 (≥)</option>
                        <option value="lte">小于等于 (≤)</option>
                        <option value="sum_eq">勾稽求和（首列=其余列按符号求和）</option>
                      </select>
                      {r.compare_op === 'sum_eq' && (
                        <input type="text" value={r.signs} onChange={(e) => update(r.id, { signs: e.target.value })}
                          placeholder="符号，如 1,1,-1（默认全+）" className="input" />
                      )}
                    </div>
                  </div>
                )}

                {r.rule_type === 'threshold' && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <select value={r.threshold_type}
                        onChange={(e) => update(r.id, { threshold_type: e.target.value as any })} className="input">
                        <option value="abs">绝对值超限</option>
                        <option value="pct_change">环比变化率超限</option>
                        <option value="ratio">占比超限</option>
                      </select>
                      <input type="number" value={r.max} onChange={(e) => update(r.id, { max: e.target.value })}
                        placeholder="阈值" className="input" />
                    </div>
                    {r.threshold_type !== 'abs' && (
                      <input type="text" value={r.baseline_column}
                        onChange={(e) => update(r.id, { baseline_column: e.target.value })}
                        placeholder="基准列，如：期初" className="input" />
                    )}
                  </div>
                )}

                <div className="flex gap-2">
                  <input type="text" value={r.message} onChange={(e) => update(r.id, { message: e.target.value })}
                    placeholder="自定义提示（可空）" className="input" />
                  <button type="button" onClick={() => setRules((rs) => rs.filter((x) => x.id !== r.id))}
                    disabled={rules.length === 1}
                    className="px-3 text-sm text-red-600 hover:bg-red-50 rounded disabled:opacity-30">删除</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? '校验中...' : '开始校验'}
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
