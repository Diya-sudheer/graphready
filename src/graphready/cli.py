"""GraphReady CLI: process | review | export | evaluate (Phase 0 stub)."""

import typer

app = typer.Typer(help="GraphReady: documents -> mapping-ready data for KG construction.")


@app.command()
def process(path: str):
    """Run the pipeline on a document and emit a Mapping-Ready Package."""
    raise NotImplementedError("Phase 1 - see docs/ROADMAP.md")


@app.command()
def review(package: str):
    """Launch the Streamlit validation UI for a package."""
    raise NotImplementedError("Phase 1 - see docs/ROADMAP.md")


if __name__ == "__main__":
    app()
