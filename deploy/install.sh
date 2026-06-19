#!/bin/bash
set -e

# 阿里云服务器初始化脚本
# 使用 Miniconda 管理 Python 环境，避免系统 Python 版本限制
# 执行前请先修改下面的仓库地址

PROJECT_DIR="/opt/music-game-video-helper"
REPO_URL="https://github.com/refNEON/music-game-video-helper.git"
CONDA_DIR="/opt/miniconda3"
ENV_NAME="music_video_helper"

echo "==> 更新系统"
if command -v apt &> /dev/null; then
    apt update && apt upgrade -y
elif command -v yum &> /dev/null; then
    yum update -y
fi

echo "==> 安装基础系统软件"
if command -v apt &> /dev/null; then
    apt install -y redis-server nginx git wget
    systemctl enable redis-server
    systemctl start redis-server
elif command -v yum &> /dev/null; then
    # Alibaba Cloud Linux 已自带 epel-aliyuncs-release
    yum install -y redis nginx git wget || true
    
    if systemctl list-unit-files | grep -q "^redis.service"; then
        systemctl enable redis
        systemctl start redis
    fi
    if systemctl list-unit-files | grep -q "^nginx.service"; then
        systemctl enable nginx
        systemctl start nginx
    fi
fi

echo "==> 安装 FFmpeg"
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg 已安装"
elif command -v apt &> /dev/null; then
    apt install -y ffmpeg
elif command -v yum &> /dev/null; then
    yum install -y ffmpeg || {
        echo "尝试安装 rpmfusion 源..."
        yum install -y "https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm" || true
        yum install -y ffmpeg || true
    }
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "警告：FFmpeg 安装失败，音视频处理功能会受影响。"
fi

echo "==> 安装 Miniconda"
if [ ! -d "$CONDA_DIR" ]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "$CONDA_DIR"
    rm -f /tmp/miniconda.sh
fi

# 初始化 conda
source "$CONDA_DIR/bin/activate"

echo "==> 创建 Python 3.9 环境"
if ! conda env list | grep -q "^$ENV_NAME "; then
    conda create -n "$ENV_NAME" python=3.9 -y
fi

echo "==> 克隆项目"
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，跳过克隆"
else
    git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR/backend"

echo "==> 安装 Python 依赖"
conda activate "$ENV_NAME"
pip install -r requirements.txt
# 如果你的 Redis 服务器版本较旧（< 6.0），取消下面这行注释
# pip install redis==4.6.0

echo "==> 创建上传/结果目录"
mkdir -p uploads results temp reference_audio

echo "==> 安装完成"
echo ""
echo "接下来请执行："
echo "  1. cp $PROJECT_DIR/deploy/systemd/*.service /etc/systemd/system/"
echo "  2. systemctl daemon-reload"
echo "  3. systemctl enable flask-app celery-worker && systemctl start flask-app celery-worker"
echo "  4. cp $PROJECT_DIR/deploy/nginx.conf /etc/nginx/conf.d/music-game-helper.conf"
echo "  5. nginx -t && systemctl reload nginx"
