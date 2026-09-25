import json
from functools import lru_cache
from pathlib import Path
from app.models import RegulatorRoute

DATA = Path(__file__).resolve().parents[1] / "data" / "state_regulators.json"


@lru_cache
def _regulators() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def regulator_for_state(state: str | None) -> RegulatorRoute:
    normalized = (state or "").strip().lower()
    info = _regulators().get(normalized)
    if info:
        return RegulatorRoute(
            level="state",
            regulator_name=info["name"],
            email=info.get("email"),
            website=info.get("website"),
            phone=info.get("phone"),
            address=info.get("address"),
            note="For intrastate electricity complaints in this state, NERC has transferred consumer-regulatory oversight to the State Electricity Regulator. Start with your electricity provider/DisCo complaint channel where applicable, then use the state regulator for unresolved matters.",
        )
    return RegulatorRoute(
        level="federal",
        regulator_name="Nigerian Electricity Regulatory Commission (NERC)",
        email="info@nerc.gov.ng",
        website="https://nerc.gov.ng/need-help/services/how-to-file-a-complaint/",
        phone="+234-09-462-1400 / 09-462-1410",
        address="Plot 1387, Cadastral Zone A00, Central Business District, Abuja, F.C.T, Nigeria",
        note="For states that have not completed transition to a state regulator, first complain in writing to your DisCo Customer Complaints Unit. If unresolved or delayed, escalate to the NERC Consumer Forum, then to NERC.",
    )
