#!/bin/sh
# release.sh —— 交互式发布/提交脚本
#
# 用法（在项目目录内执行）：
#   sh release.sh
#
# 行为：
#   1. 自动切到脚本所在目录（无论从哪调用）
#   2. 确认处于 git 仓库（不是则自动 git init）
#   3. 显示当前改动，提示输入本次提交说明
#   4. git add -A（遵循 .gitignore，不会提交 config.toml / NapCat.Shell / monitor.log 等）
#   5. 提交；可选择性打标签、推送到 origin
#
# 注：本脚本只依赖 POSIX sh，可用 sh / dash / bash 运行。

# 切到脚本所在目录
cd "$(dirname "$0")" || exit 1

# 确认 git 可用
if ! command -v git >/dev/null 2>&1; then
    echo "未找到 git，请先安装 git。" >&2
    exit 1
fi

# 确认在 git 仓库内，否则初始化
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "当前目录不是 git 仓库，正在初始化..."
    git init
fi

# 显示将要提交的内容
echo "===== 当前改动 (git status) ====="
git status --short
echo "================================="

# 提示输入提交说明
printf '请输入本次提交的说明 (commit message)：'
read -r MSG

# 空说明则中止
if [ -z "$MSG" ]; then
    echo "提交说明为空，已取消。"
    exit 1
fi

# 暂存（遵循 .gitignore）
git add -A

# 没有任何可提交改动则退出
if git diff --cached --quiet; then
    echo "没有可提交的改动，已退出。"
    exit 0
fi

# 提交
git commit -m "$MSG"

# 可选：打版本标签
printf '输入版本标签（如 v1.0.0，留空则不打标签）：'
read -r TAG
if [ -n "$TAG" ]; then
    git tag -a "$TAG" -m "Release $TAG"
    echo "已打标签：$TAG"
fi

# 可选：推送到远程
printf '是否推送到远程 origin？(y/N)：'
read -r PUSH
if [ "$PUSH" = "y" ] || [ "$PUSH" = "Y" ]; then
    if git remote -v | grep -q origin; then
        git push
        if [ -n "$TAG" ]; then
            git push origin "$TAG"
        fi
    else
        echo "未配置 origin 远程，跳过推送。"
    fi
fi

echo "===== 最近一次提交 ====="
git log -1 --oneline
