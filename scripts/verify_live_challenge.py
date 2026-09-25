"""Verify PowerRights live challenge gates without changing infrastructure."""
from __future__ import annotations

import json
import httpx

BASE = "https://powerrights-ng.onrender.com"


def main() -> None:
    health = httpx.get(f"{BASE}/health", timeout=60).json()
    readiness = httpx.get(f"{BASE}/api/v1/challenge/readiness", timeout=60).json()
    print("HEALTH")
    print(json.dumps(health, indent=2, ensure_ascii=False))
    print("\nCHALLENGE READINESS")
    print(json.dumps(readiness, indent=2, ensure_ascii=False))

    checks = readiness.get("checks", {})
    required_now = [
        "working_technical_artifact",
        "official_natlas_llm_configured",
        "official_natlas_asr_configured",
    ]
    missing = [name for name in required_now if not checks.get(name)]
    if missing:
        print("\nActivation gates still missing:")
        for name in missing:
            print(f" - {name}")
        raise SystemExit(2)

    count = readiness.get("validation", {}).get("competition_eligible_voice_interactions", 0)
    print(f"\nOfficial model path is active. Qualifying real voice interactions: {count}/50.")
    if count < 50:
        print("The build is ready for the real-user validation campaign; the submission is not yet complete.")
        raise SystemExit(3)
    print("\nAll enforced technical/validation qualification gates are met.")


if __name__ == "__main__":
    main()
