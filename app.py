# app.py
import os
import uuid

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from celery.result import AsyncResult

from config import Config
from celery_app import celery
from tasks import process_video_task

app = Flask(__name__)
app.config.from_object(Config)

def _ensure_dirs():
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(Config.RESULT_DIR, exist_ok=True)
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    os.makedirs(Config.REFERENCE_AUDIO_DIR, exist_ok=True)

_ensure_dirs()

def allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv"}

@app.route("/api/upload", methods=["POST"])
def upload_video():
    """
    上传视频并启动任务。
    form-data:
      - file: 视频文件
      - song_name: 歌曲名（必填，除非你直接传 reference_audio_path）
      - game_name: 可选
      - reference_audio_path: 可选
    """
    file = request.files.get("file")
    song_name = request.form.get("song_name", "").strip()
    game_name = request.form.get("game_name", "").strip() or None
    reference_audio_path = request.form.get("reference_audio_path", "").strip() or None

    if not file:
        return jsonify({"error": "缺少文件 file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "不支持的视频格式"}), 400

    if not song_name and not reference_audio_path:
        return jsonify({"error": "song_name 和 reference_audio_path 至少提供一个"}), 400

    upload_id = uuid.uuid4().hex
    upload_dir = os.path.join(Config.UPLOAD_DIR, upload_id)
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    video_path = os.path.join(upload_dir, filename)
    file.save(video_path)

    task = process_video_task.delay(
        video_path=video_path,
        song_name=song_name,
        game_name=game_name,
        reference_audio_path=reference_audio_path,
    )

    return jsonify({
        "message": "任务已创建",
        "task_id": task.id,
        "video_path": video_path,
    })

@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    查询 Celery 任务状态。
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
    对应 tasks.py 里返回的 /results/<task_id>/output.mp4
    """
    directory = os.path.join(Config.RESULT_DIR, task_id)
    return send_from_directory(directory, filename, as_attachment=False)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)