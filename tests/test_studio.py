import io
import json
import zipfile

from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def login_demo():
    response = client.post(
        "/api/developer/login",
        json={"email": "demo@edn.com", "password": "12345"},
    )
    assert response.status_code == 200


def test_dataset_studio_normalizes_instruction_and_chat_rows():
    login_demo()
    source = "\n".join([
        json.dumps({
            "instruction": "What is an API?",
            "input": "",
            "output": "An interface."
        }),
        json.dumps({
            "messages": [
                {"role": "user", "content": "Kí ni API?"},
                {"role": "assistant", "content": "API jẹ́ ọ̀nà ìbánisọ̀rọ̀ láàárín software."}
            ]
        }),
    ])
    response = client.post("/api/studio/dataset/inspect", json={"jsonl": source})
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["valid_examples"] == 2
    assert body["invalid_examples"] == 0
    assert body["stats"]["message_count"] == 4
    assert '"messages"' in body["normalized_jsonl"]


def test_dataset_studio_reports_bad_rows_without_hiding_valid_rows():
    login_demo()
    source = (
        '{"instruction":"Good","output":"Answer"}\n'
        '{"messages":[{"role":"user","content":"No assistant target"}]}\n'
    )
    body = client.post("/api/studio/dataset/inspect", json={"jsonl": source}).json()
    assert body["valid"] is False
    assert body["valid_examples"] == 1
    assert body["invalid_examples"] == 1
    assert body["errors"][0]["line"] == 2


def test_fine_tune_planner_is_locked_to_natlas():
    login_demo()
    response = client.post("/api/studio/fine-tune/plan", json={
        "examples": 1000,
        "epochs": 2,
        "batch_size": 2,
        "gradient_accumulation": 8,
        "lora_r": 16,
        "lora_alpha": 32,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "NCAIR1/N-ATLaS"
    assert body["method"] == "QLoRA"
    assert body["effective_batch_size"] == 16
    assert "fine_tuning/train_qlora.py" in body["command"]


def test_project_starter_is_a_real_zip():
    response = client.get("/api/studio/starter.zip")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert "ednai-starter/app.py" in names
        assert "ednai-starter/use_case.py" in names
        assert "ednai-starter/benchmarks/smoke.jsonl" in names
        assert "ednai-starter/data/example.jsonl" in names


def test_live_evaluation_fails_closed_without_natlas_runtime():
    login_demo()
    response = client.post("/api/studio/evaluate", json={
        "cases": [{
            "id": "capital",
            "prompt": "What is the capital of Nigeria?",
            "language": "english",
            "must_include": ["Abuja"],
        }]
    })
    assert response.status_code == 503
    assert "N-ATLaS runtime" in response.json()["detail"]


def test_speech_score_endpoint():
    response = client.post("/api/studio/speech/score", json={
        "reference": "Ka bayyana API da Hausa.",
        "hypothesis": "Ka bayyana API da Hausa",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["wer"] == 0
    assert body["cer"] == 0
    assert body["reference_words"] == 5
