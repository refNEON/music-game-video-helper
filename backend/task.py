import os
import shutil
from typing import Any, Dict, Optional
import ffmpeg
from celery import Task
from celery.utils.log import get_task_logger
from celery_app import celery
from config import Config
from audio_processor import denoise_audio, align_audio
from video_processor import analyze_video, enhance_video


try:
    from music_scraper import download_reference_audio
except Exception:
    download_reference_audio = None

logger = get_task_logger(__name__)

# ========================================
# 新版轻量任务：仅处理音频（前端负责视频混音）
# ========================================


# 一些默认配置兜底
DEFAULT_TEMP_DIR = getattr(Config, "TEMP_DIR", "./temp")
DEFAULT_RESULT_DIR = getattr(Config, "RESULT_DIR", os.path.join(DEFAULT_TEMP_DIR, "results"))
DEFAULT_RESULT_URL_PREFIX = getattr(Config, "RESULT_URL_PREFIX", "/results/")
ALIGNMENT_THRESHOLD = getattr(Config, "ALIGNMENT_THRESHOLD", 0.8)

# =========================
# 工具函数
# =========================
def _ensure_dir(path: str) -> str:
    """确保目录存在，并返回该目录路径。"""
    os.makedirs(path, exist_ok=True)
    return path

def _safe_float(value: Any, default: float = 0.0) -> float:
    """把任意值尽量安全地转成 float。"""
    try:
        return float(value)
    except Exception:
        return default

def _update_progress(task: Task, status: str, progress: float, detail: str, **extra: Any) -> None:
    """
    统一更新任务状态。
    Celery 前端/轮询接口一般就从这里读进度。
    """
    meta = {
        "status": status,
        "progress": round(progress, 4),
        "detail": detail,
    }
    meta.update(extra)
    task.update_state(state="PROGRESS", meta=meta)

def _build_task_workspace(task_id: str) -> str:
    """
    每个任务独立一个工作目录，所有中间文件都放这里。
    这样最安全，也最容易清理。
    """
    return _ensure_dir(os.path.join(DEFAULT_TEMP_DIR, "workspace", task_id))

def _build_result_dir(task_id: str) -> str:
    """
    最终结果目录。
    注意：不要放在 workspace 里，否则 finally 清理时会被删掉。
    """
    return _ensure_dir(os.path.join(DEFAULT_RESULT_DIR, task_id))

def _build_output_url(task_id: str, filename: str = "output.mp4") -> str:
    """
    生成结果文件的访问路径。
    这里默认返回相对 URL，你后面可以在 Flask 里配一个下载接口来对应它。
    """
    prefix = DEFAULT_RESULT_URL_PREFIX.rstrip("/") + "/"
    return f"{prefix}{task_id}/{filename}"

def _extract_audio_from_video(video_path: str, output_audio_path: str) -> str:
    """
    从视频里提取音频，输出为 WAV。
    这里放在 tasks.py 里，是为了让任务流程更完整、可独立运行。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    (
        ffmpeg
        .input(video_path)
        .output(
            output_audio_path,
            acodec="pcm_s16le",  # WAV 常用 PCM 编码
            ac=1,                # 单声道，便于后续做对齐
            ar=44100             # 采样率
        )
        .overwrite_output()
        .run(quiet=True)
    )

    if not os.path.exists(output_audio_path):
        raise RuntimeError("音频提取失败，输出文件未生成")

    return output_audio_path

def _resolve_reference_audio(
    song_name: str,
    workspace: str,
    reference_audio_path: Optional[str] = None,
) -> str:
    """
    获取参考音频。

    优先级：
    1. 直接使用外部传入的 reference_audio_path
    2. 使用 music_scraper.py 根据 song_name 下载/准备参考音频

    这样做的好处是：
    - 你后续可以先不写爬虫
    - 也可以先手动把参考音频传进来测试整条链路
    """
    if reference_audio_path:
        if not os.path.exists(reference_audio_path):
            raise FileNotFoundError(f"参考音频路径不存在: {reference_audio_path}")
        return reference_audio_path

    if not song_name:
        raise ValueError("未提供 song_name，也没有 reference_audio_path，无法进行音频对齐")

    if download_reference_audio is None:
        raise RuntimeError(
            "music_scraper.py 中的 download_reference_audio 尚未实现，"
            "请先补好这个函数，或者直接传入 reference_audio_path。"
        )

    downloaded_path = download_reference_audio(song_name, workspace)
    if not downloaded_path or not os.path.exists(downloaded_path):
        raise RuntimeError("参考音频下载/准备失败")

    return downloaded_path

def _normalize_alignment_result(result: Any) -> Dict[str, Any]:
    """
    统一音频对齐函数的返回值格式。
    兼容两种情况：
    1. align_audio() 直接返回 float，表示 match_ratio
    2. align_audio() 返回 dict，里面包含 match_ratio、offset 等信息
    """
    if isinstance(result, dict):
        match_ratio = _safe_float(result.get("match_ratio", 0.0))
        result["match_ratio"] = match_ratio
        result["passed"] = match_ratio >= ALIGNMENT_THRESHOLD
        return result

    match_ratio = _safe_float(result, 0.0)
    return {
        "match_ratio": match_ratio,
        "passed": match_ratio >= ALIGNMENT_THRESHOLD,
    }

def _call_denoise_audio(input_audio_path: str, output_audio_path: str) -> str:
    """
    兼容不同版本的 denoise_audio() 签名。
    你后面写 audio_processor.py 时，可以有两种风格：
    1. denoise_audio(input_path) -> output_path
    2. denoise_audio(input_path, output_path) -> output_path

    这层包装可以减少你改别的文件时的联动成本。
    """
    try:
        result = denoise_audio(input_audio_path, output_audio_path)
    except TypeError:
        result = denoise_audio(input_audio_path)

    if isinstance(result, str):
        output_audio_path = result

    if not os.path.exists(output_audio_path):
        raise RuntimeError("音频降噪失败，输出文件不存在")

    return output_audio_path

def _call_enhance_video(
    video_path: str,
    denoised_audio_path: str,
    output_video_path: str,
    video_meta: Dict[str, Any],
    alignment_info: Dict[str, Any],
    song_name: str,
    game_name: Optional[str],
    original_volume: float = 0.4,
    aligned_volume: float = 0.8,
) -> str:
    """
    兼容不同版本的 enhance_video() 签名。
    """
    try:
        result = enhance_video(
            video_path,
            denoised_audio_path,
            output_video_path,
            original_volume=original_volume,
            aligned_volume=aligned_volume,
        )
    except TypeError:
        # 兼容旧版签名
        result = enhance_video(video_path, denoised_audio_path, output_video_path)

    if isinstance(result, str):
        output_video_path = result

    if not os.path.exists(output_video_path):
        raise RuntimeError("视频增强失败，输出文件不存在")

    return output_video_path

# =========================
# 自定义 Task 基类
# =========================
class VideoProcessingTask(Task):
    """
    这个类不是必须，但很适合放一些统一行为。
    比如以后你要统一做日志、异常记录，可以继续往这里加。
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.exception("任务失败 task_id=%s, exc=%s", task_id, exc)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("任务成功 task_id=%s", task_id)
        super().on_success(retval, task_id, args, kwargs)

# =========================
# 核心任务
# =========================
@celery.task(bind=True, base=VideoProcessingTask, name="tasks.process_video_task")
def process_video_task(
    self,
    video_path: str,
    song_name: str,
    game_name: Optional[str] = None,
    reference_audio_path: Optional[str] = None,
    original_volume: float = 0.4,
    aligned_volume: float = 0.8,
) -> Dict[str, Any]:
    """
    这个任务负责整条处理流水线：

    1. 分析视频
    2. 提取视频音频
    3. 音频降噪
    4. 获取参考音频
    5. 音频对齐
    6. 判断是否达到 80% 重合
    7. 视频增强
    8. 返回结果

    参数说明：
    - video_path: 上传后保存到服务器上的视频路径
    - song_name: 目标歌曲名，用于下载/查找参考音频
    - game_name: 预留参数，后面你要做游戏场景分类可以用
    - reference_audio_path: 如果你已经有参考音频，可以直接传入，不必走爬虫
    """
    task_id = self.request.id

    workspace = _build_task_workspace(task_id)
    result_dir = _build_result_dir(task_id)
    final_output_path = os.path.join(result_dir, "output.mp4")

    # 中间文件路径
    extracted_audio_path = os.path.join(workspace, "extracted_audio.wav")
    denoised_audio_path = os.path.join(workspace, "denoised_audio.wav")
    reference_audio = None

    try:
        # 0. 基础校验
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        if not song_name and not reference_audio_path:
            raise ValueError("song_name 和 reference_audio_path 至少需要提供一个")

        # 1. 分析视频
        _update_progress(
            self,
            status="analyzing_video",
            progress=0.10,
            detail="正在分析视频参数...",
        )

        video_meta = analyze_video(video_path)
        if not isinstance(video_meta, dict):
            raise TypeError("analyze_video() 必须返回 dict")

        # 2. 提取视频原始音频
        _update_progress(
            self,
            status="extracting_audio",
            progress=0.25,
            detail="正在从视频中提取音频...",
        )

        _extract_audio_from_video(video_path, extracted_audio_path)

        # 3. 音频降噪
        _update_progress(
            self,
            status="denoising_audio",
            progress=0.45,
            detail="正在对音频进行降噪处理...",
        )

        denoised_audio_path = _call_denoise_audio(extracted_audio_path, denoised_audio_path)

        # 4. 获取参考音频
        _update_progress(
            self,
            status="loading_reference_audio",
            progress=0.60,
            detail="正在准备参考音频...",
        )

        reference_audio = _resolve_reference_audio(
            song_name=song_name,
            workspace=workspace,
            reference_audio_path=reference_audio_path,
        )

        # 5. 音频对齐
        _update_progress(
            self,
            status="aligning_audio",
            progress=0.75,
            detail="正在进行音频对齐计算...",
        )

        alignment_raw = align_audio(denoised_audio_path, reference_audio)
        alignment_info = _normalize_alignment_result(alignment_raw)

        # 提取对齐后的参考音频路径（align_audio 输出的才是要对齐混进视频的原曲）
        aligned_audio_path = (
            alignment_raw.get("output_audio_path")
            if isinstance(alignment_raw, dict)
            else None
        )

        _update_progress(
            self,
            status="aligned_audio",
            progress=0.78,
            detail=f"音频对齐完成，重合率 {alignment_info.get('match_ratio', 0):.2%}",
        )

        # 6. 视频增强
        _update_progress(
            self,
            status="enhancing_video",
            progress=0.90,
            detail="正在增强视频并生成最终结果...",
        )

        final_output_path = _call_enhance_video(
            video_path=video_path,
            denoised_audio_path=aligned_audio_path or denoised_audio_path,
            output_video_path=final_output_path,
            video_meta=video_meta,
            alignment_info=alignment_info,
            song_name=song_name,
            game_name=game_name,
            original_volume=original_volume,
            aligned_volume=aligned_volume,
        )

        # 7. 返回结果
        output_url = _build_output_url(task_id, "output.mp4")

        return {
            "status": "success",
            "task_id": task_id,
            "progress": 1.0,
            "detail": "视频处理完成",
            "output_path": final_output_path,
            "output_url": output_url,
            "video_meta": video_meta,
            "audio_alignment": alignment_info,
            "song_name": song_name,
            "game_name": game_name,
        }

    except Exception as e:
        # 不要手动设置 state="FAILURE"，直接抛出异常让 Celery 自动处理。
        # 手动设置 FAILURE 时如果 meta 里缺少 exc_type，会导致 Celery backend 崩溃。
        logger.exception("任务执行失败 task_id=%s", task_id)
        raise

    finally:
        # 只清理这个任务自己的 workspace
        # 不要删整个 TEMP_DIR，更不要删系统临时目录
        shutil.rmtree(workspace, ignore_errors=True)


# =========================
# 轻量版任务：仅处理音频（视频不上传服务器）
# =========================
@celery.task(bind=True, base=VideoProcessingTask, name="tasks.process_audio_only_task")
def process_audio_only_task(
    self,
    extracted_audio_path: str,
    song_name: str,
    game_name: Optional[str] = None,
    reference_audio_path: Optional[str] = None,
    original_volume: float = 0.4,
    aligned_volume: float = 0.8,
) -> Dict[str, Any]:
    """
    轻量版任务：前端已用 ffmpeg.wasm 从视频中提取音频并上传。
    本任务只做：降噪 → 获取参考音频 → 对齐 → 返回对齐后的音频文件。
    前端拿到对齐音频后，在本地完成与视频的混音。

    好处：
    - 上传/下载只有几 MB 音频，不再传输几百 MB 视频
    - 服务器带宽压力降低 90%+
    """
    task_id = self.request.id

    workspace = _build_task_workspace(task_id)
    result_dir = _build_result_dir(task_id)
    aligned_output_path = os.path.join(result_dir, "aligned_audio.wav")

    denoised_audio_path = os.path.join(workspace, "denoised_audio.wav")

    try:
        # 0. 基础校验
        if not os.path.exists(extracted_audio_path):
            raise FileNotFoundError(f"提取的音频文件不存在: {extracted_audio_path}")

        if not song_name and not reference_audio_path:
            raise ValueError("song_name 和 reference_audio_path 至少需要提供一个")

        # 1. 音频降噪
        _update_progress(
            self,
            status="denoising_audio",
            progress=0.20,
            detail="正在对音频进行降噪处理...",
        )

        denoised_audio_path = _call_denoise_audio(extracted_audio_path, denoised_audio_path)

        # 2. 获取参考音频
        _update_progress(
            self,
            status="loading_reference_audio",
            progress=0.45,
            detail="正在准备参考音频...",
        )

        reference_audio = _resolve_reference_audio(
            song_name=song_name,
            workspace=workspace,
            reference_audio_path=reference_audio_path,
        )

        # 3. 音频对齐
        _update_progress(
            self,
            status="aligning_audio",
            progress=0.70,
            detail="正在进行音频对齐计算...",
        )

        alignment_raw = align_audio(denoised_audio_path, reference_audio)
        alignment_info = _normalize_alignment_result(alignment_raw)

        # 对齐后的音频路径
        aligned_audio_from_result = (
            alignment_raw.get("output_audio_path")
            if isinstance(alignment_raw, dict)
            else None
        )

        # 4. 将对齐结果复制到 result 目录（不会被 workspace 清理删掉）
        _update_progress(
            self,
            status="saving_result",
            progress=0.90,
            detail=f"音频对齐完成，重合率 {alignment_info.get('match_ratio', 0):.2%}，正在保存结果...",
        )

        source_aligned = aligned_audio_from_result or denoised_audio_path
        shutil.copy2(source_aligned, aligned_output_path)

        # 5. 返回结果
        output_url = _build_output_url(task_id, "aligned_audio.wav")

        return {
            "status": "success",
            "task_id": task_id,
            "progress": 1.0,
            "detail": "音频对齐完成，请在前端完成混音",
            "output_url": output_url,
            "audio_alignment": alignment_info,
            "song_name": song_name,
            "game_name": game_name,
            "original_volume": original_volume,
            "aligned_volume": aligned_volume,
        }

    except Exception as e:
        logger.exception("音频任务执行失败 task_id=%s", task_id)
        raise

    finally:
        shutil.rmtree(workspace, ignore_errors=True)