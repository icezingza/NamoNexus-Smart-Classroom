from namo_core.modules.speech.recognizer import SpeechRecognizer


class SpeechService:
    def __init__(self) -> None:
        self.recognizer = SpeechRecognizer()

    def latest_transcript(self) -> dict:
        return self.recognizer.transcribe()
