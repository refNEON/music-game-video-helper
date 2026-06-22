# music-game-video-helper
A application helps to enhance your music game video

当前项目仍处于早期开发阶段，功能和使用方式可能会持续调整。

---
## 功能介绍
- 音频对齐：自动将游戏原曲与手元视频中的音频进行时间轴对齐
- 混音合成：将原曲音频叠加到视频上，可调节原始声音和原曲的音量比例
- 降噪处理：对提取的视频音频进行降噪，提升对齐精度
- 音频查找：根据歌曲名在参考音频目录中自动匹配对应的原曲文件

---
## 使用教程
### 安装步骤
#### 1. 克隆项目
```
git clone https://github.com/refNEON/music-game-video-helper.git
cd music-game-video-helper
```
#### 2. 安装 Python 依赖
```
cd backend
pip install -r requirements.txt
```
#### 3. 安装 Redis Server（Windows）
- 前往`https://github.com/tporadowski/redis/releases`
- 下载`Redis-x64-5.0.14.1.zip`
- 解压到任意目录（例如`backend\redis\`）

#### 4. 安装 ffmpeg
   
方式 A — 命令行安装（推荐）：`winget install ffmpeg`

方式 B — 手动安装：
- 从`https://www.gyan.dev/ffmpeg/builds/`下载`ffmpeg-release-essentials.zip`
- 解压后将`bin`目录添加到系统 PATH 环境变量

#### 5. 准备参考音频
将游戏原曲音频文件（mp3/wav/flac）放入`backend/reference_audio/`目录。处理时后端会根据歌曲名自动在这个目录中查找匹配的音频。

## 启动方式
### 修改 start.bat
`backend/start.bat`是一键启动脚本，但其中的路径需要根据你的环境修改：
```
# 将这行改成你的项目路径
cd /d "D:\project\music video helper\v0.2\backend"

# 将这行改成你的 Python 路径
set CONDA_PYTHON=C:\Users\lenovo\anaconda3\envs\music_video_helper\python.exe
```
如果你没有使用 conda，可以改为：`set CONDA_PYTHON=python`

修改后双击`start.bat`即可。

## 使用方法
- 上传视频 — 在前端页面上传你的音游手元视频（支持 mp4/mov/mkv/avi/webm）
- 填写歌曲名 — 输入该手元对应的歌曲名称，后端会在 reference_audio 目录中查找匹配的音频
- 上传音频（可选） — 也可以直接在前端上传参考音频文件，无需提前放入 reference_audio 目录
- 调节音量 — 设置原始声音和原曲音频的音量比例
- 提交处理 — 点击提交，等待处理完成

## 命令行模式（test.py）
如果不需要前端界面，也可以直接通过命令行运行：
- 在`backend/test/`目录下放入`video.mp4（手元视频）`和`music.mp3（对应原曲）`
- 运行：```cd backend
python test.py```


## 处理流程
后端会自动执行：分析视频 → 提取音轨 → 查找参考音频 → 降噪 → 音频对齐 → 混音合成最终视频

## 更新日志
### v0.2 (2026-06-13)
- 重构了前端界面
- 支持前端直接上传音频文件
- 优化了后端 API 接口
- 添加了一键启动脚本
### v0.1 (2026-05-22)
- 初步完成了视频音频部分的优化和对接
- 能够较大程度上实现音游曲原曲与手元的正确对接
