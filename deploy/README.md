# 阿里云部署步骤

所有命令都在**阿里云服务器**的控制台终端里执行。

复制命令时，**不要复制 ```bash 和 ``` 这些标记**，只复制中间的命令内容。

## 1. 登录服务器

阿里云控制台 → 你的服务器 → 远程连接 → Workbench。

用户名：`root`，密码：买服务器时设置的密码。

## 2. 安装基础软件

Alibaba Cloud Linux 已经自带了 EPEL 源，不要再装 `epel-release`，直接执行：

```bash
yum update -y
yum install -y python3 python3-pip python3-virtualenv redis nginx git
```

## 3. 安装 FFmpeg

Alibaba Cloud Linux 上 FFmpeg 可能在 EPEL 源里，试一下：

```bash
yum install -y ffmpeg
```

如果提示 `No match for argument: ffmpeg`，换这种方式：

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

## 5. 下载项目代码

```bash
cd /opt
git clone https://github.com/refNEON/music-game-video-helper.git
```

## 6. 安装 Python 依赖

```bash
cd /opt/music-game-video-helper/backend
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p uploads results temp reference_audio
```

## 7. 启动后端服务

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

## 8. 配置 Nginx

```bash
cp /opt/music-game-video-helper/deploy/nginx.conf /etc/nginx/conf.d/music-game-helper.conf
nginx -t
systemctl reload nginx
```

## 9. 访问网站

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
