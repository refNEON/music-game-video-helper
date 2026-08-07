import os
from video_processor import analyze_video, extract_audio_from_video, enhance_video
from audio_processor import denoise_audio, align_audio


def main():
    #原视频路径
    video_path = r"test/video.mp4"
    # 原视频所对应游戏版音频路径
    music_path = r"test/music.mp3"
    #输出目录
    output_dir = r"test/output"
    os.makedirs(output_dir, exist_ok=True)

    # 原视频提取音频存放路径
    extracted_audio_path = os.path.join(output_dir, "原视频音频提取.wav")
    # 对视频提取音频降噪后的路径
    denoised_extracted_path = os.path.join(output_dir, "降噪.wav")
    # 对齐后的参考音频输出路径
    aligned_music_path = os.path.join(output_dir, "对齐后音频.wav")
    # 音频整合版视频输出路径
    output_video_path = os.path.join(output_dir, "output.mp4")

    try:
        # 1. 分析视频
        info = analyze_video(video_path)
        print("视频信息：")
        print(info)

        # 2. 提取原视频音轨
        extracted = extract_audio_from_video(video_path, extracted_audio_path)
        print("提取音频完成：", extracted)

        # 3. 对从视频中提取的音频进行降噪（提高对齐精度）
        denoised_path = denoise_audio(extracted_audio_path, denoised_extracted_path)
        print("视频音频降噪完成：", denoised_path)

        # 4. 对齐音频：query=降噪后的视频音频, reference=原曲MP3
        align_result = align_audio(
            query_audio_path=denoised_extracted_path,
            reference_audio_path=music_path,
            output_audio_path=aligned_music_path
        )
        print("对齐结果：")
        print(align_result)

        # 5. 混合原视频音频 + 对齐后的音频
        out = enhance_video(
            video_path=video_path,
            denoised_audio_path=aligned_music_path,
            output_video_path=output_video_path,
            original_volume=0.4,
            aligned_volume=0.8
        )
        print("视频输出完成：", out)

    except Exception as e:
        print("处理失败：", e)

if __name__ == "__main__":
    main()