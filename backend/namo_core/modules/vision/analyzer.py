from namo_core.devices.webcam.capture import capture_frame_metadata


class VisionAnalyzer:
    def analyze_frame(self) -> dict:
        metadata = capture_frame_metadata()
        return {
            "attention_score": 0.88,
            "engagement": "focused",
            "device": metadata,
        }
