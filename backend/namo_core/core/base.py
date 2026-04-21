from dataclasses import dataclass


@dataclass(slots=True)
class ComponentStatus:
    name: str
    state: str
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "state": self.state, "detail": self.detail}
