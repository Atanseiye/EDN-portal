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
