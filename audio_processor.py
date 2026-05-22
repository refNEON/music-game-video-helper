import os
import numpy as np
import librosa
import soundfile as sf

try:
    import noisereduce as nr
    HAS_NOISEREDUCE = True
except ImportError:
    HAS_NOISEREDUCE = False

def _ensure_parent_dir(file_path: str):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

def _remove_if_exists(file_path: str):
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

def _normalize_1d(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if len(x) == 0:
        return x
    x = x - np.mean(x)
    std = np.std(x)
    if std < 1e-8:
        return x
    return x / std

def _build_feature(y: np.ndarray, sr: int, hop_length: int = 512) -> np.ndarray:
    if len(y) == 0:
        return np.zeros((14, 1), dtype=np.float32)

    if np.max(np.abs(y)) > 1e-8:
        y = y / np.max(np.abs(y))

    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    except Exception:
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop_length)

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    min_frames = min(len(onset), chroma.shape[1], len(rms))
    if min_frames <= 1:
        return np.zeros((14, 1), dtype=np.float32)

    onset = _normalize_1d(onset[:min_frames])
    rms = _normalize_1d(rms[:min_frames])
    chroma = chroma[:, :min_frames]

    for i in range(chroma.shape[0]):
        chroma[i] = _normalize_1d(chroma[i])

    feat = np.vstack([
        onset[None, :] * 2.0,
        chroma,
        rms[None, :] * 0.5
    ])
    return feat.astype(np.float32)

def _find_best_lag(query_feat: np.ndarray, ref_feat: np.ndarray, max_shift_frames=None):
    dim = min(query_feat.shape[0], ref_feat.shape[0])
    q = query_feat[:dim]
    r = ref_feat[:dim]

    total_corr = None
    for i in range(dim):
        qi = _normalize_1d(q[i])
        ri = _normalize_1d(r[i])
        corr = np.correlate(qi, ri, mode="full")
        if total_corr is None:
            total_corr = corr
        else:
            total_corr += corr

    lags = np.arange(-r.shape[1] + 1, q.shape[1])

    if max_shift_frames is not None:
        mask = np.abs(lags) <= max_shift_frames
        if np.any(mask):
            total_corr = total_corr[mask]
            lags = lags[mask]

    idx = int(np.argmax(total_corr))
    return int(lags[idx]), float(total_corr[idx])

def _refine_lag(query_y, ref_y, sr, coarse_lag_samples, radius_seconds=0.3, step_samples=128):
    radius = int(radius_seconds * sr)
    best_lag = coarse_lag_samples
    best_score = -1e18

    for lag in range(coarse_lag_samples - radius, coarse_lag_samples + radius + 1, step_samples):
        if lag >= 0:
            q_start = lag
            r_start = 0
        else:
            q_start = 0
            r_start = -lag

        if q_start >= len(query_y) or r_start >= len(ref_y):
            continue

        n = min(len(query_y) - q_start, len(ref_y) - r_start, sr * 60)
        if n < sr:
            continue

        q_seg = _normalize_1d(query_y[q_start:q_start + n])
        r_seg = _normalize_1d(ref_y[r_start:r_start + n])

        score = float(np.dot(q_seg, r_seg))
        if score > best_score:
            best_score = score
            best_lag = lag

    return int(best_lag), float(best_score)

def _apply_lag(ref_y: np.ndarray, target_length: int, lag_samples: int) -> np.ndarray:
    if lag_samples > 0:
        aligned = np.pad(ref_y, (lag_samples, 0), mode="constant")
    elif lag_samples < 0:
        cut = abs(lag_samples)
        if cut >= len(ref_y):
            aligned = np.zeros(target_length, dtype=np.float32)
        else:
            aligned = ref_y[cut:]
    else:
        aligned = ref_y

    if len(aligned) < target_length:
        aligned = np.pad(aligned, (0, target_length - len(aligned)), mode="constant")
    else:
        aligned = aligned[:target_length]

    return aligned.astype(np.float32)

def denoise_audio(audio_path: str, output_audio_path: str = None, sr: int = 44100) -> str:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频不存在: {audio_path}")

    if output_audio_path is None:
        base, _ = os.path.splitext(audio_path)
        output_audio_path = base + ".denoised.wav"

    _ensure_parent_dir(output_audio_path)
    _remove_if_exists(output_audio_path)

    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    if HAS_NOISEREDUCE:
        try:
            y = nr.reduce_noise(y=y, sr=sr, stationary=False)
        except Exception:
            pass

    peak = np.max(np.abs(y)) if len(y) > 0 else 0
    if peak > 1.0:
        y = y / peak * 0.98

    sf.write(output_audio_path, y, sr, subtype="PCM_16")
    return output_audio_path

def align_audio(
    query_audio_path: str,
    reference_audio_path: str,
    output_audio_path: str = None,
    sr: int = 44100,
    analysis_sr: int = 22050,
    hop_length: int = 512,
    max_shift_seconds: float = None,
    fine_tune: bool = True
) -> dict:
    if not os.path.exists(query_audio_path):
        raise FileNotFoundError(f"query 音频不存在: {query_audio_path}")

    if not os.path.exists(reference_audio_path):
        raise FileNotFoundError(f"reference 音频不存在: {reference_audio_path}")

    if output_audio_path is None:
        base, _ = os.path.splitext(reference_audio_path)
        output_audio_path = base + ".aligned.wav"

    _ensure_parent_dir(output_audio_path)
    _remove_if_exists(output_audio_path)

    query_y, sr = librosa.load(query_audio_path, sr=sr, mono=True)
    ref_y, _ = librosa.load(reference_audio_path, sr=sr, mono=True)

    if len(query_y) == 0:
        raise ValueError("query 音频为空")
    if len(ref_y) == 0:
        raise ValueError("reference 音频为空")

    query_a, analysis_sr = librosa.load(query_audio_path, sr=analysis_sr, mono=True)
    ref_a, _ = librosa.load(reference_audio_path, sr=analysis_sr, mono=True)

    query_feat = _build_feature(query_a, analysis_sr, hop_length=hop_length)
    ref_feat = _build_feature(ref_a, analysis_sr, hop_length=hop_length)

    max_shift_frames = None
    if max_shift_seconds is not None:
        max_shift_frames = int(max_shift_seconds * analysis_sr / hop_length)

    coarse_lag_frames, coarse_score = _find_best_lag(
        query_feat, ref_feat, max_shift_frames=max_shift_frames
    )
    coarse_lag_seconds = coarse_lag_frames * hop_length / analysis_sr
    coarse_lag_samples = int(round(coarse_lag_seconds * analysis_sr))

    if fine_tune:
        fine_lag_samples, score = _refine_lag(
            query_a, ref_a, analysis_sr, coarse_lag_samples
        )
    else:
        fine_lag_samples = coarse_lag_samples
        score = coarse_score

    lag_seconds = fine_lag_samples / analysis_sr
    lag_samples = int(round(lag_seconds * sr))

    aligned_y = _apply_lag(ref_y, len(query_y), lag_samples)

    peak = np.max(np.abs(aligned_y)) if len(aligned_y) > 0 else 0
    if peak > 1.0:
        aligned_y = aligned_y / peak * 0.98

    sf.write(output_audio_path, aligned_y, sr, subtype="PCM_16")

    return {
        "output_audio_path": output_audio_path,
        "lag_samples": lag_samples,
        "lag_seconds": lag_seconds,
        "coarse_lag_frames": coarse_lag_frames,
        "coarse_lag_seconds": coarse_lag_seconds,
        "query_duration": len(query_y) / sr,
        "reference_duration": len(ref_y) / sr,
        "output_duration": len(aligned_y) / sr,
        "score": score
    }