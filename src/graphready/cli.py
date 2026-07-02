"""GraphReady CLI: process | review | export | evaluate."""

from pathlib import Path

import typer

app = typer.Typer(help="GraphReady: documents -> mapping-ready data for KG construction.")


@app.command()
def process(
    path: Path = typer.Argument(..., exists=True, help="Document to process"),
    out: Path = typer.Option(Path("packages"), help="Root directory for output packages"),
):
    """Run the pipeline on a document and emit a Mapping-Ready Package."""
    from graphready.core.orchestrator import Orchestrator

    result = Orchestrator(out_root=out).process(path)
    record = result.record

    typer.echo(f"\npackage: {result.package_dir}")
    typer.echo(f"type:    {record.doc_type.value}")
    typer.echo(
        f"quality: pages={record.quality.n_pages} tables={record.quality.n_tables} "
        f"chars={record.quality.n_text_chars} "
        f"confidence={record.quality.overall_confidence}"
    )
    for w in record.quality.warnings:
        typer.secho(f"warning: {w}", fg=typer.colors.YELLOW)
    typer.echo("\nagent trace:")
    for d in record.trace.decisions:
        typer.echo(f"  [{d.decision}] -> {d.chosen}  ({d.reason})")


@app.command()
def review(package: Path = typer.Argument(..., exists=True)):
    """Launch the Streamlit validation UI for a package."""
    raise NotImplementedError("Phase 1 — see docs/ROADMAP.md")


if __name__ == "__main__":
    app()
