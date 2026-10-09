"""Gradio's HTTP/SSE API, without background threads or native dependencies."""
import json
import httpx

worker_transport = None


def predict(space_id, token, endpoint, data, audio_path=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.Client(headers=headers, timeout=240, transport=worker_transport) as client:
        info = client.get(f"https://huggingface.co/api/spaces/{space_id}")
        info.raise_for_status()
        host = info.json().get("host")
        if not host or not host.startswith("https://") or not host.split("/", 3)[2].endswith(".hf.space"):
            raise RuntimeError("Hosted runtime did not supply a trusted Space URL")
        base = host.rstrip("/") + "/gradio_api"
        if audio_path is not None:
            with open(audio_path, "rb") as stream:
                upload = client.post(base + "/upload", files={"files": ("audio.wav", stream)})
            upload.raise_for_status()
            data[0] = {"path": upload.json()[0], "meta": {"_type": "gradio.FileData"}}
        queued = client.post(base + "/call/" + endpoint, json={"data": data})
        queued.raise_for_status()
        event_id = queued.json()["event_id"]
        response = client.get(base + "/call/" + endpoint + "/" + event_id)
        response.raise_for_status()
        event = ""
        for line in response.text.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                value = json.loads(line[5:].strip())
                if event == "error":
                    raise RuntimeError(str(value))
                if event == "complete":
                    return value[0]
        raise RuntimeError("Hosted runtime ended without a complete result")
