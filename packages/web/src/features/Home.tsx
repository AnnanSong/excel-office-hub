import { Link } from 'react-router-dom'

const features = [
  {
    title: '智能拆分',
    desc: '按列、按行数或按 Sheet 拆分 Excel，输出 ZIP 打包下载。',
    href: '/split',
    status: '可用',
  },
  {
    title: '多文件汇总',
    desc: '多个 Excel 纵向堆叠，自动去重、字段映射、生成异常表。',
    href: '/aggregate',
    status: '可用',
  },
  {
    title: '批量建表',
    desc: '按名称列表批量创建工作表，可预设统一表头。',
    href: '/create-sheets',
    status: '可用',
  },
  {
    title: '报表分发与催办',
    desc: '拆分后自动按邮箱批量发送邮件。（开发中）',
    href: '#',
    status: '规划中',
  },
  {
    title: '数据比对',
    desc: '按关键字段匹配，忽略行顺序对比版本差异。（开发中）',
    href: '#',
    status: '规划中',
  },
  {
    title: '数据校验',
    desc: '可视化规则引擎，输出校验报告。（开发中）',
    href: '#',
    status: '规划中',
  },
]

export default function Home() {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Excel 办公处理中心</h1>
        <p className="mt-2 text-gray-600">把常用 Excel 办公流程搬到网页上，无需写代码即可完成批量处理。</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <Link
            key={f.title}
            to={f.href}
            className="card hover:shadow-md transition"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">{f.title}</h3>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  f.status === '可用'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {f.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-600">{f.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
