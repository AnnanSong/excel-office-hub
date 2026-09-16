# Excel 处理脚本（Vendored）

本目录下的脚本来自项目已有 skill：
`/root/.codebuddy/skills/skill_2096528888507297792/xlsx/scripts/`

已纳入文件：
- `recalc.py`：使用 LibreOffice 重算 Excel 公式
- `soffice.py`：LibreOffice 调用辅助（含沙箱环境适配）
- `helpers.py`：OOXML 包解压/重打包等通用工具

用途：后端 `packages/server/app/engines/_lib/` 会同步复制这些脚本，用于公式重算与文档校验。
