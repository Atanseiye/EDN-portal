from ednai.evals import EvalCase, score, summarize, EvalResult


def test_json_and_keyword_scoring():
    case = EvalCase(
        id="json",
        prompt="x",
        must_include=["Nigeria", "Abuja"],
        json_mode=True,
    )
    checks = score(case, '{"country":"Nigeria","capital":"Abuja"}')
    assert all(checks.values())


def test_yoruba_signal():
    case = EvalCase(id="yo", prompt="x", language="yoruba")
    checks = score(case, "Ẹ̀kọ́ yìí jẹ́ nípa imọ̀ ẹ̀rọ.")
    assert checks["language_signal"] is True


def test_summary():
    report = summarize([
        EvalResult(id="a", passed=True, text="ok", latency_ms=10, checks={"x": True}),
        EvalResult(id="b", passed=False, text="", latency_ms=30, checks={"x": False}),
    ])
    assert report["total"] == 2
    assert report["passed"] == 1
    assert report["pass_rate"] == 0.5
    assert report["median_latency_ms"] == 20
