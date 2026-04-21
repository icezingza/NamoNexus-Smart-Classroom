from namo_core.modules.tts.synthesizer import SpeechSynthesizer


class TTSService:
    def __init__(self) -> None:
        self.synthesizer = SpeechSynthesizer()

    def queue_text(self, text: str) -> dict:
        return self.synthesizer.speak(text)
