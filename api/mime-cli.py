#!/usr/bin/env python3

""" CLI for MIME backend tasks """

__version__ = "0.1"

import logging
import os

import typer
from rich.console import Console
from rich.logging import RichHandler

cli = typer.Typer(add_completion=False, no_args_is_help=True)


def get_base(input_string):
    return input_string


@cli.callback()
def common_options(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
    version: bool = typer.Option(False, "--version"),
):
    """Common options:"""

    if version:
        print(__version__)
        raise SystemExit

    log_level = logging.DEBUG if verbose else (os.getenv("LOG_LEVEL") or "INFO").upper()
    log_level = logging.CRITICAL if quiet else log_level
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(markup=False, console=Console(width=180))],
    )


@cli.command()
def do_something():
    logging.debug("debug")
    logging.info("info")


if __name__ == "__main__":
    cli()
