from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import os

from config import Config
from celery_app import celery
from celery.result import AsyncResult
from task import process_video_task

app = Flask(__name__)
# 允许跨域，方便直接打开前端 HTML 文件进行测试
CORS(app, resources=r"/*")

# 确保目录存在
os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
os.makedirs(Config.RESULT_DIR, exist_ok=True)
os.makedirs(Config.TEMP_DIR, exist_ok=True)
os.makedirs(Config.REFERENCE_AUDIO_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv"}


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


def allowed_audio_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    接收前端上传的视频和表单数据，保存后启动 Celery 异步任务。
    """
    file = request.files.get("videoFile")
    audio_file = request.files.get("audioFile")
    song_name = request.form.get("songName", "").strip()
    game_name = request.form.get("gameName", "").strip() or None
    original_volume = float(request.form.get("originalVolume", "0.4"))
    aligned_volume = float(request.form.get("alignedVolume", "0.8"))

    if not file:
        return jsonify({"error": "缺少视频文件"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "不支持的视频格式"}), 400

    # 保存上传的视频文件
    upload_id = uuid.uuid4().hex
    upload_dir = os.path.join(Config.UPLOAD_DIR, upload_id)
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    video_path = os.path.join(upload_dir, filename)
    file.save(video_path)

    # 保存上传的音频文件（如有）
    reference_audio_path = None
    if audio_file:
        if not allowed_audio_file(audio_file.filename):
            return jsonify({"error": "不支持的音频格式"}), 400
        audio_filename = secure_filename(audio_file.filename)
        reference_audio_path = os.path.join(upload_dir, audio_filename)
        audio_file.save(reference_audio_path)

    if not song_name and not reference_audio_path:
        return jsonify({"error": "song_name 和参考音频至少提供一个"}), 400

    # 启动 Celery 异步任务
    task = process_video_task.delay(
        video_path=video_path,
        song_name=song_name,
        game_name=game_name,
        reference_audio_path=reference_audio_path,
        original_volume=original_volume,
        aligned_volume=aligned_volume,
    )

    return jsonify({
        "task_id": task.id,
        "message": "任务已创建",
        "video_path": video_path,
    })


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    查询 Celery 任务状态，供前端轮询进度。
    """
    result = AsyncResult(task_id, app=celery)

    if result.state == "PENDING":
        return jsonify({
            "task_id": task_id,
            "state": "PENDING",
            "status": "waiting",
            "progress": 0.0,
            "detail": "任务等待中",
        })

    if result.state == "PROGRESS":
        info = result.info or {}
        return jsonify({
            "task_id": task_id,
            "state": "PROGRESS",
            **info,
        })

    if result.state == "SUCCESS":
        data = result.result
        return jsonify({
            "task_id": task_id,
            "state": "SUCCESS",
            **data,
        })

    if result.state == "FAILURE":
        return jsonify({
            "task_id": task_id,
            "state": "FAILURE",
            "status": "failed",
            "detail": str(result.info),
        }), 500

    return jsonify({
        "task_id": task_id,
        "state": result.state,
        "detail": str(result.info) if result.info else "",
    })


@app.route("/results/<task_id>/<path:filename>", methods=["GET"])
def download_result(task_id, filename):
    """
    下载最终结果文件。
    """
    directory = os.path.join(Config.RESULT_DIR, task_id)
    return send_from_directory(directory, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
