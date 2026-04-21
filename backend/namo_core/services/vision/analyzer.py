from namo_core.modules.vision.analyzer import VisionAnalyzer


class VisionService:
    def __init__(self) -> None:
        self.analyzer = VisionAnalyzer()

    def latest_frame_analysis(self) -> dict:
        return self.analyzer.analyze_frame()
