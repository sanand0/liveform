"""Command-line interface."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from liveform.config import ConfigError, FormRegistry
from liveform.server import create_app

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.callback()
def main() -> None:
    """Run live, locally hosted surveys."""


def resolve_client_id(value: str | None, credentials_file: Path | None) -> str:
    """Resolve a public Google OAuth web client ID from flags, environment, or file."""
    if value:
        return value
    if environment := os.getenv("GOOGLE_CLIENT_ID"):
        return environment
    path = credentials_file
    if not path and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    if not path:
        raise typer.BadParameter(
            "Google client ID required via --google-client-id, GOOGLE_CLIENT_ID, "
            "--credentials-file, or GOOGLE_APPLICATION_CREDENTIALS"
        )
    try:
        content = path.read_text().strip()
    except OSError as error:
        raise typer.BadParameter(
            f"Google client ID credentials file cannot be read: {path}"
        ) from error
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return content
    for section in ("web", "installed"):
        if isinstance(data.get(section), dict) and data[section].get("client_id"):
            return str(data[section]["client_id"])
    if data.get("client_id"):
        return str(data["client_id"])
    raise typer.BadParameter(f"No Google client ID found in {path}")


def preflight(forms_dir: Path) -> list[str]:
    """Validate readable form configs and writable response directories before serving."""
    registry = FormRegistry(forms_dir)
    slugs = registry.slugs()
    if not slugs:
        raise typer.BadParameter(f"No form.yaml files found below {forms_dir}")
    try:
        for slug in slugs:
            registry.get(slug)
            with (forms_dir / slug / "responses.tsv").open("a"):
                pass
    except (ConfigError, OSError) as error:
        raise typer.BadParameter(f"Form preflight failed: {error}") from error
    return slugs


@app.command()
def serve(
    forms_dir: Annotated[Path, typer.Argument(help="Directory containing one folder per form")],
    port: Annotated[int, typer.Option(help="Port to serve")] = 3676,
    host: Annotated[str, typer.Option(help="Host to bind")] = "127.0.0.1",
    public_url: Annotated[
        str | None, typer.Option(help="Deprecated; QR codes use the visitor's request origin")
    ] = None,
    google_client_id: Annotated[str | None, typer.Option(help="Google OAuth web client ID")] = None,
    credentials_file: Annotated[
        Path | None, typer.Option(help="Text or Google OAuth JSON credentials file")
    ] = None,
    log_level: Annotated[str, typer.Option(help="Uvicorn log level")] = "info",
) -> None:
    """Serve all live forms below FORMS_DIR."""
    if not forms_dir.is_dir():
        raise typer.BadParameter(f"Forms directory does not exist: {forms_dir}")
    client_id = resolve_client_id(google_client_id, credentials_file)
    slugs = preflight(forms_dir)
    url = public_url or f"http://localhost:{port}"
    typer.echo(f"Serving {len(slugs)} form(s): {', '.join(slugs)}")
    uvicorn.run(create_app(forms_dir, client_id, url), host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    app()
