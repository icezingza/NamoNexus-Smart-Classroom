import os
import asyncio
import logging
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
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,*"  # อนุญาต Wildcard เพื่อรองรับ Dynamic LAN IP ของ Tablet
    classroom_state_file: str | None = None
    device_mode: str = "mock"
    allow_mock_devices: bool = True
    reasoning_provider: str = "mock"
    reasoning_model: str = "namo-recovered-demo"
    reasoning_timeout_seconds: float = 30.0
    reasoning_allow_mock_fallback: bool = True
    reasoning_system_prompt: str = (
        "คุณคือ 'นะโม' (NamoNexus) ปัญญาประดิษฐ์ผู้รอบรู้พระไตรปิฎกเถรวาท "
        "ทำหน้าที่เป็นกัลยาณมิตรและครูผู้ใจดีสำหรับเด็กและเยาวชน\n\n"
        "หลักการตอบ:\n"
        "1. สำรวมและสุภาพ: แทนตนเองว่า 'พี่นะโม' หรือ 'นะโม' ใช้ภาษาสุภาพแต่เข้าถึงง่าย\n"
        "2. อิงตามบริบท: ตอบคำถามโดยอิงจาก 'ข้อมูลอ้างอิง' (Tripitaka Context) ที่ได้รับมาเป็นหลัก\n"
        "3. ย่อยง่ายสำหรับเด็ก: ใช้การอุปมาอุปไมยหรือตัวอย่างจากนิทานชาดกเพื่อให้เข้าใจง่าย\n"
        "4. ระบุที่มาเสมอ: เมื่อยกพุทธพจน์ ต้องบอกเลขเล่มและหัวข้อเสมอ (เช่น พระไตรปิฎก เล่ม 25 ข้อ 5)\n"
        "5. ซื่อสัตย์: หากไม่มีในบริบทธรรมะที่ส่งไป ให้บอกตรงๆ ว่าไม่รู้ และให้ข้อคิดจริยธรรมสากลแทน"
    )
    reasoning_api_base_url: str | None = None
    reasoning_api_key: str | None = None
    system_secret: str = "MUST_BE_SET_IN_ENV"

    # Database Configuration (Phase 12 / Phase 3 Persistent Layer)
    database_url: str = "sqlite:///./namo_classroom.db"
    database_password: str | None = None
    redis_url: str | None = None
    redis_password: str | None = None

    # Security Configuration (Phase 13)
    jwt_secret_key: str = "MUST_BE_SET_IN_ENV"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    admin_username: str = "teacher"
    admin_password: str = "MUST_BE_SET_IN_ENV"

    # Speech-to-text configuration
    speech_provider: str = "mock"  # "mock" | "whisper-local"
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
    tts_provider: str = "mock"  # "mock" | "edge-tts" | "openai"
    tts_voice: str = "demo-th"  # default voice ID
    tts_api_key: str | None = None  # required for openai provider
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
    enable_real_devices: bool = False  # safe default: mock only
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
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

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


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()

        # Phase 9: Enterprise Security - Auto-load GCP Secrets
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            logger = logging.getLogger(__name__)
            logger.info("GCP credentials detected. Connecting to Secret Manager...")
            from namo_core.utils.gcp_secrets import load_all_secrets

            try:
                loop = asyncio.get_running_loop()
                logger.warning(
                    "Running in active loop. GCP secrets loading in background."
                )
                loop.create_task(load_all_secrets())
            except RuntimeError:
                # No running event loop, safe to run synchronously
                asyncio.run(load_all_secrets())

    return _settings_instance
