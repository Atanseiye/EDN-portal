"""Stage repository modules for Pywrangler without modifying application sources."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "deploy/cloudflare/runtime"
target.mkdir(exist_ok=True)
for name in ("server", "ednai", "fine_tuning", "docs", "benchmarks", "examples"):
    destination = target / name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(root / name, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
web = target / "web"
web.mkdir(exist_ok=True)
(web / "__init__.py").write_text("")
shutil.copyfile(root / "deploy/cloudflare/worker.py", target / "worker.py")
