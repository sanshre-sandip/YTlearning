"""Voice I/O: push-to-talk recording, Whisper STT, Piper TTS."""

import sys
import tempfile
import threading
import wave
from pathlib import Path

import sounddevice as sd
import soundfile as sf
import numpy as np

from src.config import WHISPER_MODEL, PROJECT_ROOT

# ── Lazy-loaded singletons ──────────────────────────────────────────
_whisper_model = None
_piper_voice = None
_piper_loaded = False


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"  Loading Whisper model '{WHISPER_MODEL}'...")
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        print("  Whisper ready.")
    return _whisper_model


def _get_piper():
    global _piper_voice, _piper_loaded
    if not _piper_loaded:
        from piper import PiperVoice
        from piper.download_voices import download_voice

        voice_name = "en_US-lessac-medium"  # good default voice
        voice_dir = PROJECT_ROOT / "piper_voices"
        voice_dir.mkdir(exist_ok=True)

        model_path = voice_dir / f"{voice_name}.onnx"
        config_path = voice_dir / f"{voice_name}.onnx.json"

        if not model_path.exists():
            print(f"  Downloading Piper voice '{voice_name}'...")
            download_voice(voice_name, voice_dir)
            print("  Voice downloaded.")

        print("  Loading Piper TTS...")
        _piper_voice = PiperVoice.load(str(model_path), str(config_path), download_dir=str(voice_dir))
        _piper_loaded = True
        print("  Piper TTS ready.")
    return _piper_voice


# ── Recorder ────────────────────────────────────────────────────────

def _record_worker(samplerate: int, blocksize: int, stop_event: threading.Event, channels: int) -> list[np.ndarray]:
    """Record audio chunks until stop_event is set."""
    chunks: list[np.ndarray] = []

    def callback(indata, frames, _time, status):
        if status:
            print(f"  Audio status: {status}", file=sys.stderr)
        chunks.append(indata.copy())

    with sd.InputStream(samplerate=samplerate, channels=channels, blocksize=blocksize, callback=callback):
        stop_event.wait()
    return chunks


def record_until_enter() -> Path | None:
    """Press Enter to start recording, Enter again to stop.

    Returns the path to a temporary WAV file, or None if cancelled.
    """
    input("  Press Enter to START recording... ")
    print("  Recording... Press Enter again to STOP.")

    samplerate = 16000
    channels = 1
    blocksize = 1024

    stop_event = threading.Event()
    chunks: list[np.ndarray] = []

    def _record():
        nonlocal chunks
        chunks = _record_worker(samplerate, blocksize, stop_event, channels)

    record_thread = threading.Thread(target=_record, daemon=True)
    record_thread.start()

    try:
        input()
    finally:
        stop_event.set()

    record_thread.join(timeout=5)

    if not chunks:
        print("  No audio captured.")
        return None

    audio = np.concatenate(chunks, axis=0)
    tmp = Path(tempfile.mktemp(suffix=".wav"))
    sf.write(str(tmp), audio, samplerate)
    print(f"  Captured {len(audio) / samplerate:.1f}s of audio.")
    return tmp


# ── Speech-to-Text (Whisper) ───────────────────────────────────────

def transcribe(audio_path: Path, language: str | None = None) -> str:
    """Transcribe an audio file using Whisper. Returns the text."""
    model = _get_whisper()
    result = model.transcribe(str(audio_path), language=language)
    text: str = result.get("text", "").strip()
    return text


# ── Text-to-Speech (Piper) ─────────────────────────────────────────

def speak(text: str, play: bool = True) -> Path | None:
    """Convert text to speech using Piper TTS.

    If play=True, also plays the audio. Returns the path to the generated WAV file.
    """
    if not text.strip():
        return None

    voice = _get_piper()
    out_path = Path(tempfile.mktemp(suffix=".wav"))

    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    if play and out_path.exists():
        data, sr = sf.read(str(out_path))
        sd.play(data, int(sr))
        sd.wait()

    return out_path


# ── Convenience: record + transcribe in one call ───────────────────

def record_and_transcribe() -> str | None:
    """Push-to-talk, then transcribe with Whisper."""
    audio_path = record_until_enter()
    if audio_path is None:
        return None
    try:
        text = transcribe(audio_path)
        print(f"  You said: {text}")
        return text
    finally:
        audio_path.unlink(missing_ok=True)
