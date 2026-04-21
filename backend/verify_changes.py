"""Direct verification of all implementation changes (no pytest needed)."""
import sys
import traceback

passed = []
failed = []

def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"  ✓ {name}")
    else:
        failed.append(name)
        print(f"  ✗ {name}" + (f": {detail}" if detail else ""))


print("\n=== 1. Settings ===")
try:
    from namo_core.config.settings import Settings
    s = Settings()
    check("reasoning_timeout_seconds exists", hasattr(s, "reasoning_timeout_seconds"))
    check("reasoning_timeout_seconds default = 30.0", s.reasoning_timeout_seconds == 30.0)
    check("reasoning_allow_mock_fallback exists", hasattr(s, "reasoning_allow_mock_fallback"))
    check("reasoning_system_prompt exists", hasattr(s, "reasoning_system_prompt"))
except Exception:
    failed.append("settings import")
    traceback.print_exc()


print("\n=== 2. Factory Metadata ===")
try:
    from namo_core.services.reasoning.providers.factory import build_reasoning_provider
    provider, meta = build_reasoning_provider(s)
    check("factory: name present", "name" in meta)
    check("factory: active_provider present", "active_provider" in meta)
    check("factory: configured_provider present", "configured_provider" in meta)
    check("factory: active_provider == mock", meta.get("active_provider") == "mock")

    # Incomplete config fallback
    s2 = Settings(reasoning_provider="openai-compatible", reasoning_api_base_url="http://localhost/v1", reasoning_api_key=None)
    p2, m2 = build_reasoning_provider(s2)
    check("factory fallback: uses mock", p2.name == "mock")
    check("factory fallback: missing_configuration present", "missing_configuration" in m2)
    check("factory fallback: configured_provider == openai-compatible", m2.get("configured_provider") == "openai-compatible")
    check("factory fallback: missing list contains api_key", "reasoning_api_key" in m2.get("missing_configuration", []))
except Exception:
    failed.append("factory check")
    traceback.print_exc()


print("\n=== 3. Reasoning Service ===")
try:
    from namo_core.services.reasoning.reasoner import ReasoningService
    payload = ReasoningService().explain("mindfulness")
    check("reasoner: answer present", "answer" in payload)
    check("reasoner: provider_metadata present", "provider_metadata" in payload)
    check("reasoner: active_provider present", "active_provider" in payload.get("provider_metadata", {}))
    check("reasoner: provider == mock", payload.get("provider") == "mock")
except Exception:
    failed.append("reasoner check")
    traceback.print_exc()


print("\n=== 4. Engine Pipeline ===")
try:
    from namo_core.engines.namonexus.engine import NamoNexusEngine
    from namo_core.engines.fusion.engine import FusionEngine
    from namo_core.engines.resonance.engine import ResonanceEngine
    from namo_core.engines.empathy.engine import EmpathyEngine

    # Default path (guide-lesson intent)
    p = {"query": "mindfulness"}
    p = NamoNexusEngine().process(p)
    check("namonexus: default intent = guide-lesson", p["intent"] == "guide-lesson", p.get("intent"))

    p = FusionEngine().process(p)
    check("fusion: signals_merged = True", p["signals_merged"] is True)

    p["perception"] = {"attention_score": 0.88}
    p["transcript"] = {"confidence": 0.93}
    p = ResonanceEngine().process(p)
    check("resonance: score > 0", p["resonance_score"] > 0, str(p["resonance_score"]))
    check("resonance: score computed from signals", p["resonance_score"] != 0.84)

    p = EmpathyEngine().process(p)
    check("empathy: tone = calm (high resonance)", p["tone"] == "calm", p.get("tone"))
    check("empathy: student_state = attentive", p["student_state"] == "attentive")

    # Low resonance path
    p2 = {"resonance_score": 0.2}
    p2 = EmpathyEngine().process(p2)
    check("empathy: tone = concerned (low resonance)", p2["tone"] == "concerned", p2.get("tone"))

    # Quiz intent
    p3 = {"query": "quiz me on the Four Noble Truths"}
    p3 = NamoNexusEngine().process(p3)
    check("namonexus: quiz intent detected", p3["intent"] == "quiz-lesson", p3.get("intent"))
except Exception:
    failed.append("engine pipeline check")
    traceback.print_exc()


print(f"\n=== Results: {len(passed)} passed, {len(failed)} failed ===")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
