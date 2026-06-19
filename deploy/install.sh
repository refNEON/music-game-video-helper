#!/bin/bash
set -e

# 阿里云服务器初始化脚本
# 支持 Ubuntu / Debian / CentOS / Alibaba Cloud Linux
# 执行前请先修改下面的仓库地址

PROJECT_DIR="/opt/music-game-video-helper"
REPO_URL="https://github.com/refNEON/music-game-video-helper.git"

echo "==> 更新系统"
if command -v apt &> /dev/null; then
    apt update && apt upgrade -y
elif command -v yum &> /dev/null; then
    yum update -y
fi

echo "==> 安装基础依赖"
if command -v apt &> /dev/null; then
    apt install -y python3 python3-pip python3-venv redis-server nginx git
    systemctl enable redis-server
    systemctl start redis-server
elif command -v yum &> /dev/null; then
    # Alibaba Cloud Linux 已自带 epel-aliyuncs-release，不需要再装 epel-release
    if ! rpm -qa | grep -q epel-aliyuncs-release; then
        yum install -y epel-release || true
    fi
    
    # 分步安装，避免一个包失败导致全部失败
    yum install -y python3 python3-pip python3-virtualenv redis nginx git || true
    
    # 启动服务
    if systemctl list-unit-files | grep -q "^redis.service"; then
        systemctl enable redis
        systemctl start redis
    fi
    if systemctl list-unit-files | grep -q "^nginx.service"; then
        systemctl enable nginx
        systemctl start nginx
    fi
fi

echo "==> 尝试安装 FFmpeg"
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg 已安装"
elif command -v apt &> /dev/null; then
    apt install -y ffmpeg
elif command -v yum &> /dev/null; then
    # Alibaba Cloud Linux 上 FFmpeg 可能在 epel 源里
    yum install -y ffmpeg || {
        echo "注意：通过 yum 安装 FFmpeg 失败，尝试安装 rpmfusion 源..."
        yum install -y "https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm" || true
        yum install -y ffmpeg || true
    }
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "警告：FFmpeg 安装失败，音视频处理功能会受影响。请手动安装 FFmpeg 后再试。"
fi

echo "==> 克隆项目"
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，跳过克隆"
else
    git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR/backend"

echo "==> 创建 Python 虚拟环境"
if command -v apt &> /dev/null; then
    python3 -m venv venv
else
    virtualenv venv || python3 -m venv venv
fi

source venv/bin/activate

echo "==> 安装 Python 依赖"
pip install -r requirements.txt
# 如果你的 Redis 服务器版本较旧（< 6.0），取消下面这行注释
# pip install redis==4.6.0

echo "==> 创建上传/结果目录"
mkdir -p uploads results temp reference_audio

echo "==> 安装完成"
echo ""
echo "接下来请执行："
echo "  1. cp $PROJECT_DIR/v0.2/deploy/systemd/*.service /etc/systemd/system/"
echo "  2. systemctl daemon-reload"
echo "  3. systemctl enable flask-app celery-worker && systemctl start flask-app celery-worker"
echo "  4. cp $PROJECT_DIR/v0.2/deploy/nginx.conf /etc/nginx/conf.d/music-game-helper.conf"
echo "  5. nginx -t && systemctl reload nginx"
