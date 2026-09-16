#!/usr/bin/env bash
# ============================================================
# Excel Office Hub · 一键推送脚本
# 用法：双击运行，或在终端执行  bash push-to-github.sh
# 作用：自动初始化、提交并把代码推送到你的 GitHub 仓库
# ============================================================
set -e

# 颜色
G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; N='\033[0m'

echo -e "${G}=========================================${N}"
echo -e "${G}  Excel Office Hub · GitHub 一键推送${N}"
echo -e "${G}=========================================${N}"
echo ""

# ---------- 0. 环境检查 ----------
if ! command -v git >/dev/null 2>&1; then
  echo -e "${R}✗ 未检测到 git。请先安装 Git：https://git-scm.com/downloads${N}"
  exit 1
fi
echo -e "${G}✓ git 已安装${N}"

# ---------- 1. 收集必要信息 ----------
if [ -z "$1" ]; then
  echo ""
  echo "请输入你的 GitHub 仓库地址。"
  echo "格式：https://github.com/你的用户名/excel-office-hub.git"
  echo "（先在 GitHub 建好空仓库，不要勾选 Add README）"
  echo ""
  read -r -p "仓库地址: " REPO_URL
else
  REPO_URL="$1"
fi

if [ -z "$REPO_URL" ]; then
  echo -e "${R}✗ 仓库地址不能为空${N}"
  exit 1
fi

if [ -z "$2" ]; then
  read -r -p "提交信息（直接回车用默认）: " MSG
  MSG="${MSG:-init: Excel Office Hub 初版}"
else
  MSG="$2"
fi

echo ""
echo -e "${Y}仓库地址: $REPO_URL${N}"
echo -e "${Y}提交信息: $MSG${N}"
echo ""

# ---------- 2. 初始化 git 仓库（如果还没有）----------
if [ ! -d ".git" ]; then
  echo -e "${G}→ 初始化 git 仓库...${N}"
  git init -q
  git branch -M main 2>/dev/null || git checkout -b main 2>/dev/null || true
else
  echo -e "${G}→ 已存在 git 仓库，跳过初始化${N}"
fi

# 确保在 main 分支
git checkout -b main 2>/dev/null || git branch -M main 2>/dev/null || true

# ---------- 3. 配置远程 ----------
echo -e "${G}→ 配置远程仓库...${N}"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

# ---------- 4. 提交所有改动 ----------
echo -e "${G}→ 添加并提交文件...${N}"
git add -A
if git diff --cached --quiet 2>/dev/null; then
  echo -e "${Y}  （没有需要提交的改动）${N}"
else
  git -c user.name="${GIT_AUTHOR_NAME:-Excel Office Hub}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-dev@excel-office-hub.local}" \
      commit -q -m "$MSG"
  echo -e "${G}✓ 已提交${N}"
fi

# ---------- 5. 推送 ----------
echo ""
echo -e "${G}→ 开始推送到 GitHub...${N}"
echo -e "${Y}  如需输入密码，请使用 Personal Access Token，不是账号密码${N}"
echo -e "${Y}  生成方法见 docs/部署指南-GitHub-Pages-Render.md${N}"
echo ""

if git push -u origin main; then
  echo ""
  echo -e "${G}=========================================${N}"
  echo -e "${G}  ✓ 推送成功！${N}"
  echo -e "${G}=========================================${N}"
  echo ""
  echo "下一步："
  echo "  1. GitHub 仓库 → Settings → Pages → Source 选 GitHub Actions"
  echo "  2. 按 docs/部署指南-GitHub-Pages-Render.md 部署 Render 后端"
  echo "  3. 配置 VITE_API_BASE 和 CORS_ORIGINS 完成接线"
  echo ""
else
  echo ""
  echo -e "${R}✗ 推送失败${N}"
  echo "常见原因："
  echo "  - 仓库地址写错"
  echo "  - 认证失败：密码需用 Personal Access Token（勾选 repo 权限）"
  echo "  - 公司网络屏蔽 github.com：尝试换网络或用手机热点"
  exit 1
fi

# 清理可能的凭据缓存提示
if [ -f .git/config ] && grep -q "@github.com" .git/config 2>/dev/null; then
  echo -e "${Y}提示：远程 URL 中可能含明文凭据，建议执行：${N}"
  echo -e "${Y}  git remote set-url origin $REPO_URL${N}"
fi
