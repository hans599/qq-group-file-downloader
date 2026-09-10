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
#
# repository url: https://github.com/hans599/qq-group-file-downloader.git
# ---------------------------------------------------------------
# 【初次使用：克隆仓库】
#   如果这是你第一次获取本项目，需要先 clone：
#
#     git clone <仓库地址>
#     cd <项目目录>
#     sh release.sh
#
#   例如：
#     git clone https://github.com/username/repo.git
#     cd repo
#     sh release.sh
#
#   注意：
#     - clone 后已自动关联 origin 远程，无需再 git init
#     - 如果仓库是私有的，需先配置好 SSH key 或使用 token
#
# ---------------------------------------------------------------
# 【日常更新：拉取远程改动】
#   如果仓库已存在，且远程有其他人的更新，提交前建议先拉取：
#
#     git pull
#     sh release.sh
#
#   或者在脚本运行前手动执行：
#     git pull origin main     # main 换成你的分支名
#
#   推荐流程：
#     1) git pull               # 先同步远程最新改动
#     2) sh release.sh          # 再运行本脚本提交
#
#   注意：
#     - 如果本地有未提交改动，git pull 可能冲突，建议先提交或 stash
#     - 如果远程分支与本地不一致，可先 git fetch 查看状态
#
# ---------------------------------------------------------------
# 【完整工作流示例】
#   初次：  git clone <地址> && cd <目录> && sh release.sh
#   更新：  git pull && sh release.sh
#
# ---------------------------------------------------------------

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