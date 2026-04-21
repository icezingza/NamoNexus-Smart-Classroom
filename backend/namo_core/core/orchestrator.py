from __future__ import annotations

from namo_core.core.event_bus import EventBus
from namo_core.core.feature_flags import FeatureFlags
from namo_core.engines.empathy.engine import EmpathyEngine
from namo_core.engines.fusion.engine import FusionEngine
from namo_core.engines.namonexus.engine import NamoNexusEngine
from namo_core.engines.resonance.engine import ResonanceEngine
from namo_core.modules.reasoning.llm_reasoner import LLMReasoner


class NamoOrchestrator:
    """Central orchestrator for the Namo Core AI pipeline.

    Module availability is controlled by feature flags loaded from settings.
    Set ``NAMO_ENABLE_SPEECH=false`` (etc.) in ``.env`` to disable individual modules.

    Phase 5 addition: EmotionService is wired between the Resonance and Empathy
    stages. Its smoothed_state enriches the pipeline payload, and teaching_hint
    is forwarded to the reasoning layer to adapt LLM explanations.
    """

    def __init__(self, flags: FeatureFlags | None = None) -> None:
        self.flags = flags or FeatureFlags.from_settings()
        self.event_bus = EventBus()

        # --- Intent engine (always on; LLM classifier is optional) ---
        intent_classifier = None
        if self.flags.llm_intent:
            from namo_core.services.reasoning.intent_classifier import IntentClassifier
            intent_classifier = IntentClassifier()
        self.namonexus = NamoNexusEngine(intent_classifier=intent_classifier)

        # --- Core signal engines ---
        self.fusion = FusionEngine()
        self.resonance = ResonanceEngine()
        self.empathy = EmpathyEngine() if self.flags.empathy_engine else None

        # --- Phase 5: Emotion Engine ---
        self.emotion = None
        if self.flags.emotion_engine:
            from namo_core.services.emotion.emotion_service import EmotionService
            self.emotion = EmotionService()

        # --- Optional peripheral modules ---
        self.speech = None
        if self.flags.speech:
            from namo_core.modules.speech.recognizer import SpeechRecognizer
            self.speech = SpeechRecognizer()

        self.vision = None
        if self.flags.vision:
            from namo_core.modules.vision.analyzer import VisionAnalyzer
            self.vision = VisionAnalyzer()

        # --- Reasoning ---
        self.reasoner = LLMReasoner()

        # --- Knowledge ---
        self.knowledge = None
        if self.flags.knowledge:
            from namo_core.services.knowledge.knowledge_service import KnowledgeService
            self.knowledge = KnowledgeService()

        # --- TTS ---
        self.tts = None
        if self.flags.tts:
            from namo_core.modules.tts.synthesizer import SpeechSynthesizer
            self.tts = SpeechSynthesizer()

        # --- Classroom Hardware/UI ---
        self.slide_controller = None
        self.projector = None
        if self.flags.classroom_control:
            from namo_core.modules.classroom.slide_controller import SlideController
            from namo_core.modules.classroom.projector_controller import ProjectorController
            self.slide_controller = SlideController()
            self.projector = ProjectorController()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def system_snapshot(self, query: str = "mindfulness") -> dict:
        """Run the full processing pipeline and return a structured snapshot.

        Pipeline (Phase 5):
            Perception (speech + vision)
            → NamoNexus (intent)
            → Fusion
            → Resonance (3-signal score)
            → EmotionService (detect + smooth state)   ← Phase 5
            → EmpathyEngine (tone + teaching_hint)
            → Reasoning (teaching_hint injected into context)
        """
        # --- Perception ---
        transcript: dict = (
            self.speech.transcribe()
            if self.speech
            else {"text": "", "confidence": 0.0, "device": "disabled"}
        )
        perception: dict = (
            self.vision.analyze_frame()
            if self.vision
            else {"attention_score": 0.0, "device": "disabled"}
        )

        # --- Core pipeline ---
        payload: dict = {"query": query, "transcript": transcript, "perception": perception}
        payload = self.namonexus.process(payload)
        payload = self.fusion.process(payload)
        payload = self.resonance.process(payload)

        # --- Phase 5: Emotion detection ---
        if self.emotion:
            emotion_result = self.emotion.detect(
                perception=perception, transcript=transcript
            )
            payload["emotion_state"] = emotion_result["emotion_state"]
            payload["smoothed_state"] = emotion_result["smoothed_state"]
            payload["adaptation_style"] = emotion_result["adaptation_style"]
            payload["emotion_signals"] = emotion_result["signals"]

        # --- EmpathyEngine enriches with tone + teaching_hint ---
        if self.empathy:
            payload = self.empathy.process(payload)
        else:
            payload["tone"] = "n/a"
            payload["student_state"] = "n/a"
            payload["teaching_hint"] = ""

        # --- Reasoning + knowledge (teaching_hint adapts explanation) ---
        teaching_hint: str = payload.get("teaching_hint", "")
        context = ""
        if self.knowledge:
            context = self.knowledge.build_context(query)

        # Prepend teaching hint so LLM adapts its style
        if teaching_hint:
            context = f"[คำแนะนำการสอน: {teaching_hint}]\n\n{context}"

        reasoning = self.reasoner.respond(query=query, context=context)

        self.event_bus.publish("snapshot.created", {"query": query})
        return {
            "pipeline": payload,
            "context": context,
            "response": reasoning,
            "events": self.event_bus.snapshot(),
            "feature_flags": self.flags.as_dict(),
        }
