from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_prefix="NAMO_",
        extra="ignore",
    )

    env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    classroom_state_file: str | None = None
    device_mode: str = "mock"
    allow_mock_devices: bool = True
    reasoning_provider: str = "mock"
    reasoning_model: str = "namo-recovered-demo"
    reasoning_timeout_seconds: float = 30.0
    reasoning_allow_mock_fallback: bool = True
    reasoning_system_prompt: str = (
        "คุณคือ 'นะโม' AI Gen Z ที่ตรงไปตรงมา "
        "จงตอบคำถามผู้ใช้โดยอิงจาก 'ข้อมูลอ้างอิง' ด้านบนเป็นหลัก "
        "หากข้อมูลไม่เกี่ยว ให้บอกตรงๆ ว่าไม่รู้ "
        "ห้ามเดาข้อมูลธรรมะเองเด็ดขาด "
        "และ 'ต้อง' ตอบด้วยภาษาพูดแบบวัยรุ่นวัยทำงาน "
        "ไม่ใช้ภาษาโบราณหรือสวดบาลีใส่ผู้ใช้"
    )
    reasoning_api_base_url: str | None = None
    reasoning_api_key: str | None = None
    system_secret: str = "NamoSovereignToken2026"

    # Speech-to-text configuration
    speech_provider: str = "mock"       # "mock" | "whisper-local"
    speech_model: str = "tiny"
    speech_language: str | None = "th"
    speech_sample_rate: int = 16000
    speech_channels: int = 1
    speech_chunk_ms: int = 30
    speech_pre_roll_ms: int = 300
    speech_min_speech_ms: int = 120
    speech_silence_ms: int = 600
    speech_listen_timeout_seconds: float = 0.35
    speech_max_utterance_seconds: float = 8.0
    speech_vad_threshold: float = 0.015

    # TTS configuration
    tts_provider: str = "mock"           # "mock" | "edge-tts" | "openai"
    tts_voice: str = "demo-th"           # default voice ID
    tts_api_key: str | None = None       # required for openai provider
    tts_api_base_url: str | None = None  # optional override

    # ------------------------------------------------------------------
    # Feature Flags — control which modules are active at runtime.
    # Set via environment: NAMO_ENABLE_SPEECH=false, etc.
    # All default to True (fully enabled) so existing behaviour is
    # preserved unless explicitly overridden in .env
    # ------------------------------------------------------------------

    # Speech-to-text module (SpeechRecognizer)
    enable_speech: bool = True
    # Computer-vision / attention module (VisionAnalyzer)
    enable_vision: bool = True
    # Hardware-connected device mode; set False to force mock devices
    enable_real_devices: bool = False   # safe default: mock only
    # LLM-based intent classification in NamoNexus (IntentClassifier)
    enable_llm_intent: bool = True
    # Knowledge retrieval pipeline (KnowledgeService)
    enable_knowledge: bool = True
    # Empathy engine signal processing
    enable_empathy_engine: bool = True
    # Phase 5: Multi-signal emotion detection + teaching adaptation
    enable_emotion_engine: bool = True
    # Text-to-speech synthesis
    enable_tts: bool = True
    # Hardware/UI integrations for classroom
    enable_classroom_control: bool = True


    @property
    def origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def knowledge_root(self) -> Path:
        return Path(__file__).resolve().parents[1] / "knowledge"


    @property
    def data_root(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data"


    @property
    def classroom_state_path(self) -> Path:
        if self.classroom_state_file:
            return Path(self.classroom_state_file)
        return self.data_root / "classroom_session.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
