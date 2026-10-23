"""The `tokencost` command.

Runs offline against the bundled pricing file. Token counting downloads its
tokenizer vocabulary once, on first use.
"""

import json
import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from tokencost import __version__
from tokencost.cli.format import format_compact, format_int, format_usd, parse_count
from tokencost.core.config import Settings
from tokencost.core.repository import PricingDataError
from tokencost.core.schemas import (
    CompareRequest,
    Estimate,
    EstimateRequest,
    ModelInfo,
)
from tokencost.core.service import ModelNotFoundError, PricingService
from tokencost.core.tokenizer import count_tokens

app = typer.Typer(
    help="Estimate and compare token costs across AI providers.",
    no_args_is_help=True,
    add_completion=False,
)
# soft_wrap: leave line breaking to the terminal so messages stay greppable.
stdout = Console(highlight=False, soft_wrap=True)
stderr = Console(stderr=True, highlight=False, soft_wrap=True)

# Replaced in tests to pin the date used for staleness checks.
today: Callable[[], date] = date.today

# Request fields as the user typed them, for error messages.
_OPTION_NAMES = {
    "input_tokens": "--input",
    "output_tokens": "--output",
    "requests_per_day": "--per-day",
    "model_ids": "MODEL_IDS",
}


def _count_option(value: str) -> int:
    try:
        return parse_count(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None


InputTokens = Annotated[
    int,
    typer.Option(
        "--input",
        "-i",
        parser=_count_option,
        metavar="TOKENS",
        help="Input tokens per request, e.g. 3000, 3k, 1.5M.",
    ),
]
OutputTokens = Annotated[
    int,
    typer.Option(
        "--output",
        "-o",
        parser=_count_option,
        metavar="TOKENS",
        help="Output tokens per request.",
    ),
]
PerDay = Annotated[
    int | None,
    typer.Option(
        "--per-day",
        "-d",
        parser=_count_option,
        metavar="REQUESTS",
        help="Requests per day; adds daily and 30-day totals.",
    ),
]
AsJson = Annotated[
    bool, typer.Option("--json", help="Print JSON (same shape as the REST API).")
]


def _version(value: bool) -> None:
    if value:
        typer.echo(f"tokencost {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version, is_eager=True, help="Show the version."
        ),
    ] = False,
) -> None:
    """Estimate and compare token costs across AI providers."""


@app.command()
def models(as_json: AsJson = False) -> None:
    """List models and their prices per million tokens."""
    infos = _service().list_models()
    if as_json:
        _print_json(infos)
        return

    table = Table(title="Prices per 1M tokens (USD)", title_justify="left")
    # Ids are what people copy into other commands, so never truncate them.
    table.add_column("Model", no_wrap=True)
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Long prompts")
    table.add_column("Checked", no_wrap=True)
    for info in infos:
        tier = info.long_context
        table.add_row(
            escape(info.id),
            format_usd(info.input_price_per_million),
            format_usd(info.output_price_per_million),
            "-"
            if tier is None
            else f"{format_usd(tier.input_price_per_million)} / "
            f"{format_usd(tier.output_price_per_million)}\n"
            f"over {format_compact(tier.above_input_tokens)} input",
            _checked(info),
        )
    stdout.print(table)
    _print_notes(infos)


@app.command()
def estimate(
    model_id: Annotated[
        str,
        typer.Argument(metavar="MODEL_ID", help="Model id; see `tokencost models`."),
    ],
    input_tokens: InputTokens,
    output_tokens: OutputTokens,
    per_day: PerDay = None,
    as_json: AsJson = False,
) -> None:
    """Estimate the cost of a request on one model."""
    service = _service()
    result = _call(
        lambda: service.estimate(
            EstimateRequest(
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                requests_per_day=per_day,
            )
        )
    )
    if as_json:
        _print_json(result)
        return

    stdout.print(
        f"[bold]{escape(result.model_name)}[/bold] ({escape(result.provider)})"
    )
    table = Table.grid(padding=(0, 2))
    table.add_column()
    table.add_column(justify="right")
    table.add_column(justify="right")
    table.add_row(
        "Input",
        f"{format_int(result.input_tokens)} tokens",
        format_usd(result.input_cost_usd),
    )
    table.add_row(
        "Output",
        f"{format_int(result.output_tokens)} tokens",
        format_usd(result.output_cost_usd),
    )
    table.add_row(
        "[bold]Per request[/bold]",
        "",
        f"[bold]{format_usd(result.total_cost_usd)}[/bold]",
    )
    if result.projection is not None:
        p = result.projection
        table.add_row(
            "Per day",
            f"{format_int(p.requests_per_day)} requests",
            format_usd(p.daily_cost_usd),
        )
        table.add_row(
            "[bold]Per month[/bold]",
            f"{p.days_per_month} days",
            f"[bold]{format_usd(p.monthly_cost_usd)}[/bold]",
        )
    stdout.print(table)
    if result.price_tier == "long_context":
        stdout.print("Long-prompt pricing applies to this request size.")
    _print_footer([result])


@app.command()
def compare(
    model_ids: Annotated[
        list[str] | None,
        typer.Argument(
            metavar="[MODEL_ID]...", help="Models to compare; all when omitted."
        ),
    ] = None,
    *,
    input_tokens: InputTokens,
    output_tokens: OutputTokens,
    per_day: PerDay = None,
    as_json: AsJson = False,
) -> None:
    """Compare the same usage across models, cheapest first."""
    service = _service()
    result = _call(
        lambda: service.compare(
            CompareRequest(
                model_ids=model_ids or None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                requests_per_day=per_day,
            )
        )
    )
    if as_json:
        _print_json(result)
        return

    projected = per_day is not None
    table = Table(
        title=f"{format_int(input_tokens)} input + {format_int(output_tokens)} "
        "output tokens per request",
        title_justify="left",
    )
    table.add_column("Model")
    table.add_column("Provider")
    table.add_column("Per request", justify="right")
    if projected:
        table.add_column("Per day", justify="right")
        table.add_column("Per month", justify="right")
    for e in result.estimates:
        cheapest = e.model_id in result.cheapest_model_ids
        style = "bold green" if cheapest else None
        marker = " *" if e.price_tier == "long_context" else ""
        row = [
            escape(e.model_id),
            escape(e.provider),
            format_usd(e.total_cost_usd) + marker,
        ]
        if e.projection is not None:
            row += [
                format_usd(e.projection.daily_cost_usd),
                format_usd(e.projection.monthly_cost_usd),
            ]
        table.add_row(*row, style=style)
    stdout.print(table)
    stdout.print(f"Cheapest: {escape(', '.join(result.cheapest_model_ids))}")
    if any(e.price_tier == "long_context" for e in result.estimates):
        stdout.print("* long-prompt pricing applies to this request size")
    _print_footer(result.estimates)


@app.command()
def count(
    file: Annotated[
        str | None,
        typer.Argument(
            metavar="[FILE]",
            help="File to count; reads standard input if omitted or -.",
        ),
    ] = None,
    as_json: AsJson = False,
) -> None:
    """Approximate the number of tokens in a file or piped text."""
    if file is None or file == "-":
        if sys.stdin.isatty():
            _fail("Give a FILE, or pipe text in: cat prompt.txt | tokencost count")
        text = sys.stdin.read()
    else:
        try:
            text = Path(file).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            _fail(f"{file} is not UTF-8 text.")
        except OSError as exc:
            _fail(f"Cannot read {file}: {exc.strerror or exc}")

    try:
        result = count_tokens(text)
    except OSError as exc:
        _fail(
            "Could not load the tokenizer vocabulary. It is downloaded once on "
            f"first use, so connect to the internet and retry. ({exc})"
        )
    if as_json:
        _print_json(result)
        return

    stdout.print(
        f"[bold]{format_int(result.tokens)}[/bold] tokens "
        f"(approximate, {result.tokenizer}) · "
        f"{format_int(result.characters)} characters"
    )
    stdout.print(f"[dim]{escape(result.note)}[/dim]")


def _service() -> PricingService:
    try:
        return PricingService.from_settings(Settings(), today=lambda: today())
    except PricingDataError as exc:
        _fail(str(exc))


def _call[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except ValidationError as exc:
        problems = [
            f"{_OPTION_NAMES.get(str(err['loc'][0]), err['loc'][0])}: {err['msg']}"
            for err in exc.errors()
        ]
        _fail("; ".join(problems), code=2)
    except ModelNotFoundError as exc:
        _fail(f"Unknown model {exc.model_id!r}. Run `tokencost models` to list them.")


def _checked(info: ModelInfo) -> str:
    text = info.effective_date.isoformat()
    if info.valid_until is not None:
        text += f"\nuntil {info.valid_until.isoformat()}"
    return f"{text} [red](stale)[/red]" if info.stale else text


def _print_notes(items: Sequence[ModelInfo | Estimate]) -> None:
    for item in items:
        model_id = item.id if isinstance(item, ModelInfo) else item.model_id
        if item.notes:
            stdout.print(f"[dim]Note ({escape(model_id)}): {escape(item.notes)}[/dim]")


def _print_footer(estimates: Sequence[Estimate]) -> None:
    dates = sorted({e.effective_date for e in estimates})
    stdout.print(
        f"[dim]Prices checked {', '.join(d.isoformat() for d in dates)}. "
        "Estimates, not invoices.[/dim]"
    )
    _print_notes(estimates)
    stale = [e.model_id for e in estimates if e.stale]
    if stale:
        stderr.print(
            f"[yellow]Warning:[/yellow] prices may be out of date for "
            f"{escape(', '.join(stale))}."
        )


def _print_json(data: BaseModel | Sequence[BaseModel]) -> None:
    payload = (
        data.model_dump(mode="json")
        if isinstance(data, BaseModel)
        else [item.model_dump(mode="json") for item in data]
    )
    typer.echo(json.dumps(payload, indent=2))


def _fail(message: str, code: int = 1) -> NoReturn:
    stderr.print(f"[red]Error:[/red] {escape(message)}")
    raise typer.Exit(code)
