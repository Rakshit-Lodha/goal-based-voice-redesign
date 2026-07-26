from pathlib import Path

from pypdf import PdfReader

from core import plan_pdf
from core.session import Goal, SessionState


def _complete_state() -> SessionState:
    return SessionState(
        name="Rakshit",
        monthly_income=150_000,
        monthly_expenses=70_000,
        monthly_emi=25_000,
        ratios={
            "surplus": 35_000,
            "savings_rate": 0.30,
            "savings_band": "good",
            "debt_to_income": 0.17,
            "dti_band": "good",
        },
        risk_profile="balanced",
        goals=[
            Goal(
                name="आपातकालीन निधि",
                target_amount_today=570_000,
                horizon_years=1,
                priority=1,
                inflated_target=604_200,
                projected_from_existing=604_200,
                required_sip=0,
            )
        ],
    )


def test_hindi_pdf_contains_translated_headings(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_pdf, "OUTPUT_DIR", str(tmp_path))

    path = plan_pdf.generate_pdf(_complete_state(), language="hi")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)

    assert Path(path).exists()
    assert "आपकी वित्तीय योजना" in text
    assert "वित्तीय सारांश" in text
    assert "आपके लक्ष्य" in text
