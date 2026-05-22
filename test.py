import os
from video_processor import analyze_video, extract_audio_from_video, enhance_video
from audio_processor import denoise_audio, align_audio

def main():
    video_path = r"C:\Users\lenovo\Desktop\other\project\music video helper\测试视频\00c0223a06633dc51be562a3ed0c199b.mp4"
    music_path = r"C:\Users\lenovo\Desktop\other\project\music video helper\测试视频\Reku Mochizuki - INFiNiTE ENERZY -Overdoze- (2023 Update).mp3"

    output_dir = r"C:\Users\lenovo\Desktop\other\project\music video helper\results\test"
    os.makedirs(output_dir, exist_ok=True)

    extracted_audio_path = os.path.join(output_dir, "tiqu.wav")
    denoised_music_path = os.path.join(output_dir, "music.denoised.wav")
    aligned_music_path = os.path.join(output_dir, "music.aligned.wav")
    output_video_path = os.path.join(output_dir, "output.mp4")

    try:
        # 1. 分析视频
        info = analyze_video(video_path)
        print("视频信息：")
        print(info)

        # 2. 提取原视频音轨
        extracted = extract_audio_from_video(video_path, extracted_audio_path)
        print("提取音频完成：", extracted)

        # 3. 对音乐降噪
        denoised_path = denoise_audio(music_path, denoised_music_path)
        print("降噪完成：", denoised_path)

        # 4. 对齐音频
        align_result = align_audio(
            query_audio_path=extracted_audio_path,
            reference_audio_path=denoised_path,
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
            aligned_volume=1.0
        )
        print("视频输出完成：", out)

    except Exception as e:
        print("处理失败：", e)

if __name__ == "__main__":
    main()