"""Speech-to-text backends used by SpeechRecognizer."""

from __future__ import annotations

import importlib
import math
import threading

import numpy as np


class GoogleSTTTranscriber:
    """Google Cloud Speech-to-Text provider for Hybrid Expansion."""

    name = "google-cloud"

    def __init__(self, language: str | None = "th") -> None:
        self.language = language or "th-TH"
        if len(self.language) == 2:
            self.language = f"{self.language}-{self.language.upper()}"  # e.g. th-TH

        try:
            speech_module = importlib.import_module("google.cloud.speech")
            self.client = speech_module.SpeechClient()
            self.speech = speech_module
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "google-cloud-speech package is not installed."
            ) from exc
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Google Cloud credentials not found for STT."
            )
            raise RuntimeError(f"GCP init failed: {exc}") from exc

    def transcribe_pcm16(self, audio_bytes: bytes, sample_rate: int) -> dict:
        if not audio_bytes:
            return {"text": "", "confidence": 0.0, "language": self.language}

        audio = self.speech.RecognitionAudio(content=audio_bytes)
        config = self.speech.RecognitionConfig(
            encoding=self.speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code=self.language,
        )

        try:
            response = self.client.recognize(config=config, audio=audio)

            text = ""
            confidence = 0.0

            for result in response.results:
                text += result.alternatives[0].transcript
                if confidence == 0.0:
                    confidence = result.alternatives[0].confidence
                else:
                    confidence = (confidence + result.alternatives[0].confidence) / 2

            return {
                "text": text.strip(),
                "confidence": round(confidence, 3) if text else 0.0,
                "language": self.language,
                "segments": len(response.results),
            }
        except Exception as exc:
            import logging

            logging.getLogger(__name__).error(f"Google STT failed: {exc}")
            return {"text": "", "confidence": 0.0, "language": self.language}


class MockSpeechTranscriber:
    name = "mock"

    def transcribe_pcm16(self, audio_bytes: bytes, sample_rate: int) -> dict:
        del audio_bytes, sample_rate
        return {
            "text": "Please explain the Four Noble Truths.",
            "confidence": 0.93,
        }


class FasterWhisperTranscriber:
    """CTranslate2-based Whisper — เร็วกว่า openai-whisper 2-4x บน CPU"""

    name = "faster-whisper"

    def __init__(self, model_name: str = "tiny", language: str | None = "th") -> None:
        self.model_name = model_name
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def _load_model(self):
        from faster_whisper import WhisperModel  # noqa: PLC0415

        with self._lock:
            if self._model is None:
                self._model = WhisperModel(
                    self.model_name, device="cpu", compute_type="int8"
                )
        return self._model

    def transcribe_pcm16(self, audio_bytes: bytes, sample_rate: int) -> dict:
        """แปลง PCM16 bytes → float32 numpy → transcribe"""
        if not audio_bytes:
            return {"text": "", "confidence": 0.0, "language": self.language}
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return self._run(audio)

    def transcribe_file(self, path: str) -> dict:
        """Transcribe โดยตรงจากไฟล์เสียง (mp3/wav/etc.)"""
        return self._run(path)

    def _run(self, audio) -> dict:
        model = self._load_model()
        segments, info = model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            condition_on_previous_text=False,  # ป้องกันการจำคำเดิมมาพูดซ้ำ (ลด Loop Hallucination)
            initial_prompt="บทเรียนธรรมะ พระไตรปิฎก อริยสัจ ๔ พุทธศาสนา",  # ไกด์คำศัพท์ให้ตรงบริบทห้องเรียน
            temperature=0.0,  # บังคับไม่ให้ AI สุ่มเดาคำเพื่อลดการจินตนาการข้อความเอง
            compression_ratio_threshold=2.4,  # ตัดข้อความทิ้งทันทีหากเกิดการพิมพ์ซ้ำๆ ติดลูป
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.35,
                min_speech_duration_ms=250,
                min_silence_duration_ms=1000,
                speech_pad_ms=400,
            ),
        )
        segs = list(segments)
        text = "".join(s.text for s in segs).strip()
        confidence = (
            round(
                sum(math.exp(max(s.avg_logprob, -5.0)) for s in segs)
                / max(len(segs), 1),
                3,
            )
            if segs
            else (0.5 if text else 0.0)
        )
        return {
            "text": text,
            "confidence": confidence,
            "language": info.language,
            "segments": len(segs),
        }


class WhisperSpeechTranscriber:
    name = "whisper-local"

    def __init__(self, model_name: str = "tiny", language: str | None = "th") -> None:
        self.model_name = model_name
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def transcribe_pcm16(self, audio_bytes: bytes, sample_rate: int) -> dict:
        if not audio_bytes:
            return {"text": "", "confidence": 0.0, "language": self.language}

        if sample_rate != 16000:
            raise RuntimeError("WhisperSpeechTranscriber expects 16kHz PCM audio.")

        whisper = importlib.import_module("whisper")
        model = self._load_model(whisper)
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        result = model.transcribe(
            audio=audio,
            fp16=False,
            language=self.language or None,
            task="transcribe",
            verbose=False,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        text = (result.get("text") or "").strip()
        segments = result.get("segments") or []
        return {
            "text": text,
            "confidence": self._confidence_from_segments(
                segments=segments, has_text=bool(text)
            ),
            "language": result.get("language", self.language),
            "segments": len(segments),
        }

    def _load_model(self, whisper) -> object:
        with self._lock:
            if self._model is None:
                self._model = whisper.load_model(self.model_name)
            return self._model

    def _confidence_from_segments(self, segments: list[dict], has_text: bool) -> float:
        if not segments:
            return 0.0 if not has_text else 0.5

        scores = []
        for segment in segments:
            avg_logprob = float(segment.get("avg_logprob", -1.0))
            scores.append(max(0.0, min(1.0, math.exp(avg_logprob))))

        return round(sum(scores) / len(scores), 3)
