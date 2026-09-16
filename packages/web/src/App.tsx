import { Link, Route, Routes } from 'react-router-dom'
import Home from './features/Home'
import SplitPage from './features/split/SplitPage'
import AggregatePage from './features/aggregate/AggregatePage'
import MergePage from './features/merge/MergePage'
import ComparePage from './features/compare/ComparePage'
import ValidatePage from './features/validate/ValidatePage'
import CreateSheetsPage from './features/createSheets/CreateSheetsPage'

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-excel-600 text-white shadow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-14 items-center justify-between">
            <Link to="/" className="text-lg font-bold tracking-tight">
              Excel 办公处理中心
            </Link>
            <nav className="hidden sm:flex gap-6 text-sm font-medium">
              <Link to="/split" className="hover:text-green-100">智能拆分</Link>
              <Link to="/aggregate" className="hover:text-green-100">多文件汇总</Link>
              <Link to="/merge" className="hover:text-green-100">多表合并</Link>
              <Link to="/compare" className="hover:text-green-100">数据比对</Link>
              <Link to="/validate" className="hover:text-green-100">数据校验</Link>
              <Link to="/create-sheets" className="hover:text-green-100">批量建表</Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/split" element={<SplitPage />} />
          <Route path="/aggregate" element={<AggregatePage />} />
          <Route path="/merge" element={<MergePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/validate" element={<ValidatePage />} />
          <Route path="/create-sheets" element={<CreateSheetsPage />} />
        </Routes>
      </main>

      <footer className="border-t bg-white py-4">
        <div className="mx-auto max-w-7xl px-4 text-center text-xs text-gray-500">
          Excel Office Hub · MVP 阶段
        </div>
      </footer>
    </div>
  )
}

export default App
