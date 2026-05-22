import os
import json
import ffmpeg

def _ensure_parent_dir(file_path: str):
    """
    确保输出目录存在
    """
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

def _remove_if_exists(file_path: str):
    """
    如果文件已存在，先删除，避免 ffmpeg 写入失败
    """
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

def analyze_video(video_path: str) -> dict:
    """
    分析视频基本信息
    返回:
        {
            "path": ...,
            "duration": ...,
            "size": ...,
            "video_stream": {...},
            "audio_stream": {...}
        }
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    probe = ffmpeg.probe(video_path)

    format_info = probe.get("format", {})
    streams = probe.get("streams", [])

    video_stream = None
    audio_stream = None

    for s in streams:
        if s.get("codec_type") == "video" and video_stream is None:
            video_stream = s
        elif s.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = s

    def _safe_float(v, default=None):
        try:
            return float(v)
        except Exception:
            return default

    result = {
        "path": video_path,
        "duration": _safe_float(format_info.get("duration")),
        "size": int(format_info["size"]) if "size" in format_info else None,
        "bit_rate": int(format_info["bit_rate"]) if "bit_rate" in format_info else None,
        "video_stream": None,
        "audio_stream": None
    }

    if video_stream:
        result["video_stream"] = {
            "codec_name": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "pix_fmt": video_stream.get("pix_fmt"),
            "r_frame_rate": video_stream.get("r_frame_rate"),
            "avg_frame_rate": video_stream.get("avg_frame_rate"),
            "duration": _safe_float(video_stream.get("duration")),
        }

    if audio_stream:
        result["audio_stream"] = {
            "codec_name": audio_stream.get("codec_name"),
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
            "channel_layout": audio_stream.get("channel_layout"),
            "duration": _safe_float(audio_stream.get("duration")),
        }

    return result

def extract_audio_from_video(
    video_path: str,
    output_audio_path: str,
    audio_sample_rate: int = 44100
) -> str:
    """
    从视频中提取音频，输出为 wav
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    _ensure_parent_dir(output_audio_path)
    _remove_if_exists(output_audio_path)

    # 提取为标准 wav，更适合后续对齐和混音
    (
        ffmpeg
        .input(video_path)
        .output(
            output_audio_path,
            vn=None,
            acodec="pcm_s16le",
            ar=audio_sample_rate,
            ac=1
        )
        .overwrite_output()
        .run(quiet=True)
    )

    return output_audio_path

def mix_audio_with_video(
    video_path: str,
    aligned_audio_path: str,
    output_video_path: str,
    original_volume: float = 0.5,
    aligned_volume: float = 1.0,
    audio_bitrate: str = "192k"
) -> str:
    """
    将原视频音频与已经对齐好的音频混合后输出新视频。

    参数:
        video_path: 原视频路径
        aligned_audio_path: 已经对齐好的音频路径
        output_video_path: 输出视频路径
        original_volume: 原视频音量（建议 0.2~0.6）
        aligned_volume: 对齐音频音量（建议 0.7~1.2）
        audio_bitrate: 输出音频码率
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if not os.path.exists(aligned_audio_path):
        raise FileNotFoundError(f"对齐音频不存在: {aligned_audio_path}")

    _ensure_parent_dir(output_video_path)
    _remove_if_exists(output_video_path)

    # 输入原视频
    video_input = ffmpeg.input(video_path)

    # 输入对齐后的音频
    aligned_input = ffmpeg.input(aligned_audio_path)

    # 原视频音频降一点音量
    original_audio = video_input.audio.filter("volume", original_volume)

    # 对齐音频降/增音量
    aligned_audio = aligned_input.audio.filter("volume", aligned_volume)

    # 混音
    mixed_audio = ffmpeg.filter(
        [original_audio, aligned_audio],
        "amix",
        inputs=2,
        duration="first",
        dropout_transition=0
    )

    (
        ffmpeg
        .output(
            video_input.video,     # 原视频画面
            mixed_audio,           # 混合后的音频
            output_video_path,
            vcodec="copy",         # 视频流直接拷贝
            acodec="aac",          # 音频编码
            audio_bitrate=audio_bitrate,
            movflags="+faststart"
        )
        .overwrite_output()
        .run(quiet=True)
    )

    return output_video_path

def enhance_video(
    video_path: str,
    denoised_audio_path: str,
    output_video_path: str,
    original_volume: float = 0.5,
    aligned_volume: float = 1.0
) -> str:
    """
    兼容你原来的调用方式。
    实际功能：把原视频音频和 denoised_audio_path（对齐好的音频）混合后输出视频。
    """
    return mix_audio_with_video(
        video_path=video_path,
        aligned_audio_path=denoised_audio_path,
        output_video_path=output_video_path,
        original_volume=original_volume,
        aligned_volume=aligned_volume
    )