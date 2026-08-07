# music-game-video-helper
A application helps to enhance your music game video

当前项目仍处于早期开发阶段，功能和使用方式可能会持续调整。

---
## 功能介绍
简化音游手元视频的处理，便于普通玩家发布高质量的音游手元。
- 强化手元音乐声，同时保留视频原声
- 对总体视频声音进行降噪处理
- 略微提升视频质量，可以完成基础的视频参数调整

---
## 使用教程
### 安装依赖
- 0.安装python，如果你的电脑上没有python，请先下载python，在安装时勾选!!!!!Add to PATH!!!!!!
- 1.安装必要依赖，进入backend文件夹，点击上方路径栏，清空之后输入cmd，打开当前目录的cmd指令栏，使用pip install -r requirements.txt进行安装
- 2.安装Redis Server，前往https://github.com/tporadowski/redis/releases下载Redis-x64-5.0.14.1.zip，并解压至backend\redis\
- 3.安装ffmpeg，同时按下win和r，随后输入cmd，再输入winget install ffmpeg命令进行安装。如此方法失效，则请手动前往https://www.gyan.dev/ffmpeg/builds/下载ffmpeg-releaseessentials.zip，解压后将bin目录添加到系统PATH环境变量
- 4.修改bat文件，将bat文件修改为txt格式，用记事本打开，找到  cd /d"xxxxxxxxxxx"  行，将/d后面替换为backend所在完整路径。
### 正常使用
- 点击start.bat文件,等待四个窗口运行，无报错后点击cupnb.html，即可进行使用

---
## 更新日志
### v0.1 (2026-05-22)
- 初步完成了视频音频部分的优化和对接
- 能够较大程度上实现音游曲原曲与手元的正确对接
### v0.2 (2026-06-22)
- 可以直接通过前端文件进行处理，对小白更加友好了
- 解决了fetch故障
- 本版本于2026-08-08重新找回，为当前最稳定的可使用版本
- 于2026-08-08更新了readme
