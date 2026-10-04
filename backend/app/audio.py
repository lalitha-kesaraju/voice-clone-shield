"""Audio pipeline: load -> energy VAD -> ECAPA-TDNN speaker embedding (CPU).

The heavy ML model is lazy-loaded on first use so the API boots even without
torch/speechbrain installed; enrollment and matching raise a clear error then.
"""
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from .config import settings

_model = None  # singleton EncoderClassifier


# ---------- loading / resampling ----------

def load_mono_16k(path: str) -> tuple[np.ndarray, int]:
    """Load any soundfile-readable audio as mono float32 at 16 kHz, peak-normalised."""
    data, sr = sf.read(path, always_2d=False)
    data = np.asarray(data, dtype=np.float32)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != settings.TARGET_SR:
        g = gcd(int(sr), settings.TARGET_SR)
        data = resample_poly(data, settings.TARGET_SR // g, int(sr) // g).astype(np.float32)
    peak = float(np.max(np.abs(data)) if data.size else 0.0)
    if peak > 0:
        data = data / peak * 0.9
    return data, settings.TARGET_SR


# ---------- energy VAD ----------

def energy_vad(
    wave: np.ndarray, sr: int = 16000, frame_ms: int = 30, thresh_db: float = -42.0
) -> tuple[float, np.ndarray]:
    """Return (voiced_ratio, voiced_waveform) using frame-RMS energy gating.

    Clips with mostly silence / pure instrumental beds get a low voiced_ratio,
    which the API surfaces so the artist knows the clip may be unsuitable.
    """
    frame = int(sr * frame_ms / 1000)
    if wave.size < frame:
        return 0.0, wave
    n = wave.size // frame
    frames = wave[: n * frame].reshape(n, frame)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20.0 * np.log10(rms + 1e-12)
    voiced = db > thresh_db
    ratio = float(voiced.mean()) if n else 0.0
    voiced_wave = frames[voiced].reshape(-1) if voiced.any() else wave
    return ratio, voiced_wave.astype(np.float32)


# ---------- ECAPA-TDNN embedding ----------

def _get_model():
    global _model
    if _model is None:
        try:
            import torch  # noqa: F401  (ensures the compute backend exists)
            from speechbrain.inference import EncoderClassifier
        except ImportError as exc:
            raise RuntimeError(
                "Speaker-embedding model dependencies are missing. "
                "Install them with: "
                "pip install torch --index-url https://download.pytorch.org/whl/cpu && "
                "pip install speechbrain"
            ) from exc
        _model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": "cpu"},
        )
    return _model


def embed_waveform(wave: np.ndarray) -> np.ndarray:
    """L2-normalised 192-dim speaker embedding for one waveform chunk."""
    model = _get_model()  # raises a clear RuntimeError if torch/speechbrain are missing
    import torch

    sig = torch.from_numpy(np.asarray(wave, dtype=np.float32)).unsqueeze(0)
    with torch.no_grad():
        emb = model.encode_batch(sig).squeeze().cpu().numpy().astype(np.float32)
    norm = float(np.linalg.norm(emb))
    return (emb / norm).astype(np.float32) if norm > 0 else emb


def embed_clip(path: str) -> tuple[np.ndarray, float, float]:
    """Full pipeline for one audio file.

    Returns (embedding, duration_sec, voiced_ratio). Long clips are embedded in
    30s chunks and averaged for a stable voiceprint.
    """
    wave, sr = load_mono_16k(path)
    duration = wave.size / sr
    voiced_ratio, voiced = energy_vad(wave, sr)

    if voiced_ratio < settings.MIN_VOICED_RATIO:
        raise ValueError(
            f"Too little voiced audio detected ({voiced_ratio:.0%}). "
            "Upload a clip with clear vocals, not silence or a pure instrumental."
        )
    if voiced.size / sr < settings.MIN_VOICED_SECONDS:
        raise ValueError(
            f"Only {voiced.size / sr:.1f}s of voiced audio found; "
            f"need at least {settings.MIN_VOICED_SECONDS:.0f}s."
        )

    chunk = settings.CHUNK_SECONDS * sr
    embs = []
    for start in range(0, voiced.size, chunk):
        seg = voiced[start : start + chunk]
        if seg.size < sr * 3:  # skip tiny tail
            continue
        embs.append(embed_waveform(seg))
    if not embs:
        raise ValueError("Could not extract a speaker embedding from this clip.")
    mean_emb = np.mean(np.stack(embs), axis=0)
    mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-12)
    return mean_emb.astype(np.float32), float(duration), float(voiced_ratio)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)


def band_for(score: float) -> str:
    if score >= settings.MATCH_THRESHOLD:
        return "likely_match"
    if score >= settings.REVIEW_THRESHOLD:
        return "review"
    return "no_match"
