# Excel 办公处理中心

基于 GitHub 生态的可交互 Excel 办公处理网站，把常用 Excel 批量操作搬到网页上。

## 已实现功能（MVP）

| 模块 | 说明 |
|---|---|
| **智能拆分** | **按列（支持多列组合，如 L+AD+H）、按行数、按工作表拆分，保留原表格式，文件名支持笔数命名** |
| 多文件汇总 | 多个 Excel 纵向堆叠，自动文件去重、业务主键去重、生成异常表 |
| **多表合并汇总** | **遍历每个文件全部 Sheet，按归一化名称分组分别汇总；去重、缺失标红、导入日志、模板填充保格式** |
| 批量建表 | 按名称列表批量创建工作表，可预设统一表头 |

### 智能拆分增强（ExcelSplitSkill）

对应 VBA 的「按组合列拆分」场景，重点解决格式丢失问题：

- **多列组合拆分**：`columns` 支持多列（如 `部门,岗位,职级`，或 Excel 列字母 `L,AD,H`），按组合值分组，文件名自动拼接
- **保留原表格式**：通过复制原工作表实现，完整保留字体、边框、底色、列宽、行高，**不再是 pandas 重建**
- **保留合并单元格**：表头区域的合并单元格原样保留
- **笔数命名**：文件名模板支持 `{count}` 占位符，如 `{value}_{count}笔` → `研发部_工程师_2笔.xlsx`
- **表头行可配置**：支持表头在第 3 行的模板，数据自动从下一行开始
- **空值跳过**：分组键为空的行不单独成文件
- **冻结表头**：拆出的文件可选自动冻结表头行

接口：`POST /api/split/`，文件名模板占位符 `{value}` / `{count}` / `{index}` / `{sheet}`。

### 多表合并汇总（ExcelMergeSkill）

对应 VBA 的「多公司回传文件汇总」场景，解决了简单堆叠做不到的几件事：

- **Sheet 名归一化**：自动去开头序号前缀（`1.` `2-1.`）、去末尾期间后缀（`2608` `20260831` `2026.08`）、统一大小写与横杠，把五花八门的 Sheet 名归并到同一逻辑表（即「主表-明细分别汇总」）
- **占位页跳过**：自动跳过名含 `>>>` 或黄色标签的说明页（对应 `IsSpacerSheet`）
- **表头行可配置**：很多模板表头在第 3 行，不再写死第 1 行
- **跨文件主键去重**：同一工号/项目编号在多份文件中重复时只保留一条并记录重复来源
- **缺失 Sheet 标红**：指定期望 Sheet，任一文件缺失即在报告中高亮
- **导入日志**：逐文件逐 Sheet 记录导入行数与状态（已导入/空表/跳过/读取失败）
- **模板填充保格式**：上传汇总模板后按同名 Sheet 填入数据，完整保留模板的字体、底色、列宽等格式；模板中无数据的 Sheet 标红提示

接口：`POST /api/merge/`（多文件 + 可选模板 + 配置），`GET /api/merge/download`。

## 技术栈

- **前端**：React 18 + TypeScript + Vite + TailwindCSS
- **后端**：Python 3.11 + FastAPI + openpyxl + pandas
- **公式重算**：LibreOffice（通过 vendored 的 xlsx skill `recalc.py`）
- **部署**：前端 GitHub Pages，后端 Render（Docker）

## 项目结构

```
excel-office-hub/
├── packages/
│   ├── web/          # React 前端
│   └── server/       # FastAPI 后端
├── tools/
│   └── excel-scripts/# vendored xlsx skill 脚本
├── .github/workflows/# CI/CD
├── render.yaml       # Render 部署配置
└── README.md
```

## 本地开发

### 1. 克隆并安装依赖

```bash
git clone https://github.com/YOUR_USERNAME/excel-office-hub.git
cd excel-office-hub
pnpm install
```

### 2. 启动后端

```bash
cd packages/server
pip install -e ".[dev]"
# 确保已安装 LibreOffice
uvicorn app.main:app --reload --port 8000
```

后端启动后访问 http://localhost:8000/docs 查看 API 文档。

### 3. 启动前端

```bash
pnpm dev:web
```

前端默认 http://localhost:5173，已配置代理转发 `/api` 到后端。

## 部署

### 前端 → GitHub Pages

1. 在 GitHub 仓库 **Settings → Pages → Build and deployment** 选择 **GitHub Actions**。
2. push 到 `main` 分支后，`.github/workflows/deploy-pages.yml` 会自动构建并部署。

> 若你的 Pages 域名是 `https://YOUR_USERNAME.github.io/excel-office-hu>`，工作流会自动设置 `GITHUB_PAGES_BASE`。如果绑定自定义域名，可将 `packages/web/vite.config.ts` 中的 `base` 改为 `'/'`。

### 后端 → Render

1. 在 Render 创建 **Blueprint**，选择本仓库的 `render.yaml`。
2. 在环境变量中填入你的 AI API Key（可选）：
   - `ANTHROPIC_API_KEY`
   - `GLM_API_KEY`
3. Render 会自动构建 Docker 镜像并启动后端。

### 企业私有化

```bash
cd packages/server
docker build -t excel-office-hub-server .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e ANTHROPIC_API_KEY=... \
  -v /host/data:/app/data \
  excel-office-hub-server
```

## 环境变量

复制 `.env.example` 为 `.env` 并按需填写：

| 变量 | 说明 |
|---|---|
| `VITE_API_BASE` | 前端调用的 API 地址 |
| `DATABASE_URL` | 数据库连接串 |
| `UPLOAD_DIR` | 上传文件存储目录 |
| `ANTHROPIC_API_KEY` | Claude API Key |
| `GLM_API_KEY` | 智谱 GLM API Key |
| `SMTP_*` | 邮件发送配置（可选） |

## 后续路线图

- **Phase 2**：组合列拆分增强、数据比对、数据校验、Outlook 批量发邮件
- **Phase 3**：AI 报表分析、数据预处理、企业私有化部署完善

## 许可

本项目代码采用 MIT 许可。vendored 的 xlsx skill 脚本版权归原作者所有。
