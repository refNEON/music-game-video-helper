# 阿里云部署步骤

所有命令都在**阿里云服务器**的控制台终端里执行。

复制命令时，**不要复制 ```bash 和 ``` 这些标记**，只复制中间的命令内容。

## 1. 登录服务器

阿里云控制台 → 你的服务器 → 远程连接 → Workbench。

用户名：`root`，密码：买服务器时设置的密码。

## 2. 安装基础软件

```bash
yum update -y
yum install -y redis nginx git wget
```

## 3. 安装 FFmpeg

```bash
yum install -y ffmpeg
```

如果提示找不到，换这种方式：

```bash
yum install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
yum install -y ffmpeg
```

装好后检查：

```bash
ffmpeg -version
```

## 4. 启动 Redis 和 Nginx

```bash
systemctl enable redis
systemctl start redis
systemctl enable nginx
systemctl start nginx
```

## 5. 安装 Miniconda

你的项目需要 Python 3.9，但系统自带的是 Python 3.6，所以用 Miniconda 来管理 Python 环境。

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
bash /tmp/miniconda.sh -b -p /opt/miniconda3
source /opt/miniconda3/bin/activate
conda create -n music_video_helper python=3.9 -y
```

## 6. 下载项目代码

```bash
cd /opt
git clone https://github.com/refNEON/music-game-video-helper.git
```

## 7. 安装 Python 依赖

```bash
cd /opt/music-game-video-helper/backend
source /opt/miniconda3/bin/activate music_video_helper
pip install -r requirements.txt
mkdir -p uploads results temp reference_audio
```

## 8. 启动后端服务

```bash
cp /opt/music-game-video-helper/deploy/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable flask-app celery-worker
systemctl start flask-app celery-worker
```

检查是否启动成功：

```bash
systemctl status flask-app
systemctl status celery-worker
```

## 9. 配置 Nginx

```bash
cp /opt/music-game-video-helper/deploy/nginx.conf /etc/nginx/conf.d/music-game-helper.conf
nginx -t
systemctl reload nginx
```

## 10. 访问网站

浏览器输入服务器公网 IP：

```
http://你的服务器IP
```

如果显示页面，说明成功了。

## 如果部署脚本 install.sh 已经传到服务器上

也可以直接运行：

```bash
cd /opt/music-game-video-helper/deploy
bash install.sh
```

## 打不开页面怎么办

1. 检查阿里云安全组是否放通 80 端口
2. 检查 Nginx：`systemctl status nginx`
3. 检查后端：`systemctl status flask-app`
4. 检查日志：`tail -f /var/log/nginx/error.log`
