# 部署指南：接入 GitHub 并发布可交互网页

本文档面向**无管理员权限的办公电脑**，全程只需 GitHub 网页操作 + 少量 git 命令，**无需安装 Python，无需本地跑后端**。

## 架构

```
GitHub 仓库
├── GitHub Pages  →  前端 React 静态页面（免费、自动部署）
└── Render        →  后端 FastAPI（处理 Excel，Docker 自动构建）
```

前端部署到 Pages 后，通过 `VITE_API_BASE` 指向 Render 后端地址，两者配合完成「上传 Excel → 处理 → 下载结果」的完整交互。

---

## 第一步：把代码推送到 GitHub

### 方式 0：一键脚本（最省事，推荐）

源码包里有 `push-to-github.sh`，无需记任何 git 命令：

1. 先在 GitHub 建一个空仓库（**不要**勾选 Add README）
2. 解压源码包，进入目录
3. 运行脚本（Windows 用 Git Bash 或 WSL；macOS/Linux 直接终端）：

```bash
# macOS / Linux / Git Bash
bash push-to-github.sh https://github.com/你的用户名/excel-office-hub.git
```

脚本会自动：初始化仓库 → 配置远程 → 提交 → 推送。
中途要求输密码时，粘贴你的 **Personal Access Token**（生成方法见下方「凭据说明」）。

### 方式 A：网页上传（不想用命令行）

1. 打开 https://github.com/new ，仓库名填 `excel-office-hub`，选 Public，**不要**勾选 Add a README。
2. 解压源码包，进入新仓库页面点 **uploading an existing file**。
3. 把所有文件和文件夹拖入（**注意 `.github` 是隐藏文件夹**，Windows 需先开启「显示隐藏文件」；macOS 按 `Cmd+Shift+.`）。
4. 填提交信息，点 **Commit changes**。

### 方式 B：命令行

```bash
cd excel-office-hub
git remote add origin https://github.com/YOUR_USERNAME/excel-office-hub.git
git add -A && git commit -m "init"
git branch -M main
git push -u origin main
```

> 推送密码必须用 **Personal Access Token**（GitHub 已禁用账号密码推送）。
> 生成：头像 → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token → 勾选 `repo` + `workflow` → 复制保存。

---

## 第二步：开启 GitHub Pages（前端）

1. 仓库 → **Settings** → **Pages**
2. **Source** 选 **GitHub Actions**
3. 去 **Actions** 标签，确认 `Deploy to GitHub Pages` 运行成功（约 1-2 分钟）
4. **Settings → Pages** 顶部显示访问地址：`https://YOUR_USERNAME.github.io/excel-office-hub/`

---

## 第三步：部署后端到 Render

1. https://render.com 用 GitHub 账号登录（免费，无需信用卡）
2. **New +** → **Blueprint** → 选择你的仓库（自动读取 `render.yaml`）
3. **Apply**，等待构建（首次装 LibreOffice，约 5-15 分钟）
4. 得到地址：`https://excel-office-hub-server.onrender.com`

---

## 第四步：前后端接线（最关键）

### 4.1 前端 → 后端

仓库 → **Settings** → **Secrets and variables** → **Actions** → **Variables** → **New repository variable**

| Name | Value |
|---|---|
| `VITE_API_BASE` | `https://excel-office-hub-server.onrender.com/api` |

### 4.2 后端放行前端

Render → 你的服务 → **Environment** → 修改 `CORS_ORIGINS`：

```
https://YOUR_USERNAME.github.io
```

保存后自动重新部署。

### 4.3 重新触发前端部署

GitHub 仓库 → **Actions** → `Deploy to GitHub Pages` → **Run workflow**。

---

## 第五步：访问

`https://YOUR_USERNAME.github.io/excel-office-hub/`

---

## 常见问题

**① `.github` 文件夹没上传成功（Pages 不自动部署）**
网页上传有时会漏掉隐藏文件夹。解决：直接在 GitHub 网页点 **Add file → Create new file**，文件名输入
`.github/workflows/deploy-pages.yml`，把仓库里 `deploy-pages.yml` 的内容粘进去，提交即可。

**② 页面打开是空白**
多半是 base 路径问题。确认 `deploy-pages.yml` 里 `GITHUB_PAGES_BASE=/仓库名/` 生效，或检查浏览器控制台的 404。

**③ 点处理没反应 / 报网络错误**
- 检查 `VITE_API_BASE` 是否指向 Render 地址且带 `/api` 后缀
- 检查 Render 后端是否在运行（免费版会休眠，首次访问等 30-50 秒）
- 检查 `CORS_ORIGINS` 是否包含你的 Pages 域名

**④ Render 构建失败**
- 首次构建慢是正常的（装 LibreOffice）
- 若内存不足，可在 `render.yaml` 中改用 `plan: starter`（付费）或精简单元格库

**⑤ 无管理员权限会受影响吗？**
不会。上传代码、配置 Pages、配置 Render 全是网页操作；后端跑在 Render 云端，本地无需装任何东西。
唯一可能的干扰是公司网络屏蔽 github.com，此时用 HTTPS + Token 方式一般可绕过；实在不行可换用手机热点。

**⑥ 为什么不能由 AI 助手直接帮我推送？**
AI 助手运行在隔离沙箱中，该沙箱网络策略通常不包含 github.com，因此无法直连推送。
但 GitHub OAuth 授权本身是通的，所以「下载代码包 + 本地运行一键脚本」是当前最省事且最安全的路径：
凭据留在你自己的电脑上，不经过第三方。

---

## 更新代码后如何重新部署

```bash
git add -A
git commit -m "你的改动说明"
git push
```

推送后 GitHub Pages 会自动重新构建，Render 也会自动重新部署，无需手动操作。
