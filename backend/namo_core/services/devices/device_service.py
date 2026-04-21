from importlib.util import find_spec

from namo_core.config.settings import get_settings
from namo_core.devices.microphone.capture import capture_audio_status
from namo_core.devices.projector.controller import projector_status
from namo_core.devices.webcam.capture import capture_frame_metadata


class MockDeviceAdapter:
    mode = "mock"

    def snapshot(self) -> dict:
        microphone = dict(capture_audio_status())
        microphone["provider"] = self.mode

        projector = dict(projector_status())
        projector["provider"] = self.mode

        webcam = dict(capture_frame_metadata())
        webcam["provider"] = self.mode

        return {
            "microphone": microphone,
            "projector": projector,
            "webcam": webcam,
        }


class ProbeDeviceAdapter:
    mode = "probe"

    def snapshot(self) -> dict:
        microphone_ready = bool(find_spec("pyaudio") or find_spec("sounddevice"))
        webcam_ready = bool(find_spec("cv2"))

        return {
            "microphone": {
                "device": "microphone",
                "status": "detected" if microphone_ready else "unavailable",
                "sample_rate": 16000 if microphone_ready else None,
                "channels": 1 if microphone_ready else None,
                "provider": self.mode,
            },
            "projector": {
                "device": "projector",
                "status": "unavailable",
                "source": "system-probe",
                "provider": self.mode,
            },
            "webcam": {
                "device": "webcam",
                "status": "detected" if webcam_ready else "unavailable",
                "resolution": "unknown",
                "provider": self.mode,
            },
        }


class DeviceService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def snapshot(self) -> dict:
        if self.settings.device_mode == "probe":
            probed = ProbeDeviceAdapter().snapshot()
            if self.settings.allow_mock_devices:
                return self._merge_with_mock_defaults(probed)
            return probed

        return MockDeviceAdapter().snapshot()

    def _merge_with_mock_defaults(self, probed: dict) -> dict:
        fallback = MockDeviceAdapter().snapshot()
        merged: dict = {}

        for name, device in probed.items():
            if device["status"] in {"detected", "ready"}:
                merged[name] = device
                continue

            fallback_device = dict(fallback[name])
            fallback_device["fallback_reason"] = f"{name} probe unavailable"
            fallback_device["provider"] = f"{device['provider']}+mock"
            merged[name] = fallback_device

        return merged
