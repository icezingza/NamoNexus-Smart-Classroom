from namo_core.core.base_engine import BaseEngine


class FusionEngine(BaseEngine):
    name = "fusion"

    def process(self, payload: dict) -> dict:
        updated = dict(payload)
        updated["signals_merged"] = True
        return updated
