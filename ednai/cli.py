from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .client import EDNAi
from .evals import load_jsonl, run_benchmark, summarize
from .providers import NATLAS_MODEL_ID

app = typer.Typer(help="EDNAi — developer tooling for N-ATLaS")
console = Console()


@app.command()
def chat(
    prompt: str = typer.Argument(..., help="Prompt to send to N-ATLaS"),
    base_url: str = typer.Option("http://localhost:8000", "--base-url"),
    system: str | None = typer.Option(None, "--system"),
    temperature: float = typer.Option(0.2, "--temperature"),
    max_tokens: int = typer.Option(512, "--max-tokens"),
):
    client = EDNAi(base_url)
    result = client.generate(
        prompt,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    console.print(result.text)
    console.print(f"\n[dim]{result.model} · {result.provider or 'gateway'} · {result.latency_ms} ms[/dim]")


@app.command("models")
def models_cmd(base_url: str = typer.Option("http://localhost:8000", "--base-url")):
    client = EDNAi(base_url)
    console.print_json(data=client.models())


@app.command()
def eval(
    benchmark: Path,
    base_url: str = typer.Option("http://localhost:8000", "--base-url"),
    output: Path | None = typer.Option(None, "--output"),
):
    cases = load_jsonl(benchmark)
    report = summarize(run_benchmark(EDNAi(base_url), cases))
    table = Table(title=f"EDNAi benchmark — {NATLAS_MODEL_ID}")
    table.add_column("Case")
    table.add_column("Status")
    table.add_column("Latency")
    for item in report["results"]:
        table.add_row(
            item["id"],
            "PASS" if item["passed"] else "FAIL",
            f"{item['latency_ms']} ms" if item["latency_ms"] is not None else "-",
        )
    console.print(table)
    console.print(
        f"Pass rate: [bold]{report['passed']}/{report['total']}[/bold] "
        f"({report['pass_rate']:.1%})"
    )
    if output:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"Saved report to {output}")


@app.command()
def doctor(base_url: str = typer.Option("http://localhost:8000", "--base-url")):
    client = EDNAi(base_url)
    try:
        health = client.health()
        console.print("[green]Gateway reachable[/green]")
        console.print_json(data=health)
    except Exception as exc:
        console.print(f"[red]Gateway check failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def compare(
    benchmark: Path,
    baseline_url: str = typer.Option(..., "--baseline-url"),
    candidate_url: str = typer.Option(..., "--candidate-url"),
    output: Path | None = typer.Option(None, "--output"),
):
    """Run the same benchmark against two N-ATLaS runtimes and compare them."""
    cases = load_jsonl(benchmark)
    baseline = summarize(run_benchmark(EDNAi(baseline_url), cases))
    candidate = summarize(run_benchmark(EDNAi(candidate_url), cases))

    baseline_by_id = {item["id"]: item for item in baseline["results"]}
    candidate_by_id = {item["id"]: item for item in candidate["results"]}
    changed = []
    for case in cases:
        before = baseline_by_id[case.id]
        after = candidate_by_id[case.id]
        changed.append({
            "id": case.id,
            "baseline_passed": before["passed"],
            "candidate_passed": after["passed"],
            "improved": (not before["passed"]) and after["passed"],
            "regressed": before["passed"] and (not after["passed"]),
            "baseline_latency_ms": before["latency_ms"],
            "candidate_latency_ms": after["latency_ms"],
        })

    report = {
        "benchmark": str(benchmark),
        "baseline_url": baseline_url,
        "candidate_url": candidate_url,
        "baseline_pass_rate": baseline["pass_rate"],
        "candidate_pass_rate": candidate["pass_rate"],
        "pass_rate_delta": round(candidate["pass_rate"] - baseline["pass_rate"], 4),
        "improvements": sum(1 for x in changed if x["improved"]),
        "regressions": sum(1 for x in changed if x["regressed"]),
        "cases": changed,
    }

    table = Table(title="EDNAi N-ATLaS comparison")
    table.add_column("Case")
    table.add_column("Baseline")
    table.add_column("Candidate")
    table.add_column("Change")
    for item in changed:
        change = "IMPROVED" if item["improved"] else "REGRESSED" if item["regressed"] else "—"
        table.add_row(
            item["id"],
            "PASS" if item["baseline_passed"] else "FAIL",
            "PASS" if item["candidate_passed"] else "FAIL",
            change,
        )
    console.print(table)
    console.print(
        f"Pass-rate delta: [bold]{report['pass_rate_delta']:+.1%}[/bold] · "
        f"improvements {report['improvements']} · regressions {report['regressions']}"
    )
    if output:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"Saved comparison to {output}")


@app.command("init")
def init_project(
    directory: Path = typer.Argument(Path("."), help="Directory to scaffold"),
    force: bool = typer.Option(False, "--force", help="Overwrite EDNAi starter files"),
):
    """Scaffold a minimal N-ATLaS developer project."""
    directory.mkdir(parents=True, exist_ok=True)
    benchmark_dir = directory / "benchmarks"
    benchmark_dir.mkdir(exist_ok=True)

    starter_files = {
        directory / "app.py": """from ednai import EDNAi

ai = EDNAi(base_url="http://localhost:8000")

result = ai.generate(
    "Explain what an API is in simple Nigerian English.",
    temperature=0.2,
)
print(result.text)
""",
        directory / ".env.example": "EDNAI_BASE_URL=http://localhost:8000\n",
        directory / "README.md": """# N-ATLaS project with EDNAi

1. Install EDNAi.
2. Configure or run an EDNAi N-ATLaS gateway.
3. Run `python app.py`.
4. Run `ednai eval benchmarks/smoke.jsonl --base-url http://localhost:8000`.
""",
        benchmark_dir / "smoke.jsonl": '{"id":"hello","prompt":"What is the capital of Nigeria? Answer briefly.","language":"english","must_include":["Abuja"]}\n',
    }

    written = []
    skipped = []
    for target, content in starter_files.items():
        if target.exists() and not force:
            skipped.append(str(target))
            continue
        target.write_text(content, encoding="utf-8")
        written.append(str(target))

    console.print("[green]EDNAi project scaffolded.[/green]")
    for item in written:
        console.print(f"  created {item}")
    for item in skipped:
        console.print(f"  [yellow]kept existing[/yellow] {item}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Run the EDNAi gateway, playground and developer docs."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print("[red]Server dependencies are missing.[/red] Install with: pip install -e \".[server]\"")
        raise typer.Exit(1) from exc
    uvicorn.run("server.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
