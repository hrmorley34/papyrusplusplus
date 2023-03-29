#!/usr/bin/env python3
import argparse
import logging
import subprocess
import sys
from contextlib import contextmanager
from logging import debug, info, warning
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional, TextIO, Tuple

import colorama
import yaml

from .bases import Definition


def existing_path(p: str) -> Path:
    path = Path(p)
    if not path.exists():
        raise Exception
    return path


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-f",
        "--definition",
        required=True,
        type=existing_path,
        action="append",
        help="YAML definition",
    )

    verbg = parser.add_mutually_exclusive_group()
    verbg.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help="Increase verbosity",
    )
    verbg.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        dest="verbosity",
        const=-2,
        help="Only print errors",
    )

    parser.add_argument(
        "-p",
        "--papyrus",
        default=None,
        type=existing_path,
        help="Path to PapyrusCs binary",
    )

    parser.add_argument("--dry-run", action="store_true", help="Do nothing")
    parser.add_argument(
        "--sheet-only",
        action="store_true",
        help="Generate the markers from a sheet *only*",
    )

    parser.add_argument("--skip-map", action="store_true", help="Skip map generation")
    parser.add_argument(
        "--skip-sheet", action="store_true", help="Skip player markers generation"
    )
    parser.add_argument("--skip-remote", action="store_true", help="Skip remote upload")
    parser.add_argument("--skip-webhook", action="store_true", help="Skip webhook push")

    return parser


class ArgNamespace(argparse.ArgumentParser):
    definition: List[Path]
    verbosity: int

    papyrus: Optional[Path]

    dry_run: bool
    sheet_only: bool

    skip_map: bool
    skip_sheet: bool
    skip_remote: bool
    skip_webhook: bool


class Config:
    dry_run: bool
    papyrus: Path

    sheet_only: bool
    skip_map: bool
    skip_webhook: bool
    skip_sheet: bool
    skip_remote: bool

    definitions: List[Tuple[Path, Definition]]

    @classmethod
    def from_namespace(cls, args: ArgNamespace) -> "Config":
        self = cls()

        self.dry_run = args.dry_run

        if self.dry_run and args.verbosity >= 0:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO - 10 * args.verbosity)

        if args.papyrus is None:
            # `this directory`/papyruscs/PapyrusCs(.exe)
            binsuffix = ".exe" if sys.platform.lower().startswith("win") else ""
            self.papyrus = (
                (Path(sys.argv[0]).parents[0] / "papyrusbin" / "PapyrusCs")
                .with_suffix(binsuffix)
                .absolute()
            )
        else:
            self.papyrus = args.papyrus
        debug(f"PapyrusCs path: {self.papyrus}")

        if args.sheet_only:
            self.sheet_only = True
            self.skip_map = self.skip_webhook = True
            self.skip_sheet = self.skip_remote = False

            if args.skip_map:
                warning("--skip-map implied by --sheet-only")
            if args.skip_webhook:
                warning("--skip-webhook implied by --sheet-only")
            if args.skip_sheet:
                raise Exception("--skip-sheet breaks --sheet-only")
            if args.skip_remote:
                warning("--skip-remote is against --sheet-only")
                self.skip_remote = True
        else:
            self.sheet_only = False
            self.skip_map = args.skip_map
            self.skip_sheet = args.skip_sheet
            self.skip_remote = args.skip_remote
            self.skip_webhook = args.skip_webhook

        self.definitions = []
        for path in args.definition:
            with open(path, "rb") as file:
                defi = Definition.parse_obj(yaml.load(file, yaml.SafeLoader))
            self.definitions.append((path, defi))

        return self


def initialise_output():
    colorama.init()
    LOGG = Logg()
    logging.basicConfig(handlers=[LOGG], level=logging.INFO, format="%(message)s")

    return LOGG


if TYPE_CHECKING:
    _LoggBase = logging.StreamHandler[TextIO]
else:
    _LoggBase = logging.StreamHandler


class Logg(_LoggBase):
    _outcolour = colorama.Style.BRIGHT
    _errcolour = colorama.Style.BRIGHT + colorama.Fore.RED
    _outsuffix = colorama.Style.RESET_ALL
    doingdone_active = False

    stream: TextIO

    def emit(self, record: logging.LogRecord):
        if record.levelno > 25:
            prefix = self._errcolour
        else:
            prefix = self._outcolour
        suffix = self._outsuffix

        if self.doingdone_active:
            self.doingdone_active = False
            prefix = "\n" + prefix

        # slightly nabbed from logging.StreamHandler
        try:
            msg = self.format(record)
            self.stream.write(prefix + msg + suffix + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


def _doingdone_end_handle() -> bool:
    printagain = False
    for handler in logging.getLogger().handlers:
        if isinstance(handler, Logg):
            if handler.doingdone_active:
                handler.doingdone_active = False
            else:
                printagain = True
    return printagain


@contextmanager
def doing_done(
    loggfunc: Callable[[Any], Any],
    starting: str,
    success: str = "{}done{}.".format(colorama.Fore.LIGHTGREEN_EX, colorama.Fore.RESET),
    failure: str = "{}error{}.".format(colorama.Fore.RED, colorama.Fore.RESET),
):
    try:
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.terminator = ""
            handler.acquire()
        loggfunc(starting + " ")
    finally:
        for handler in logging.getLogger().handlers:
            try:
                if isinstance(handler, logging.StreamHandler):
                    handler.terminator = "\n"
                handler.release()
            except Exception:
                pass
            finally:
                if isinstance(handler, Logg):
                    handler.doingdone_active = True
    try:
        yield
    except Exception:
        if _doingdone_end_handle():
            loggfunc(starting + " " + failure)
        else:
            loggfunc(failure)
        raise
    else:
        if _doingdone_end_handle():
            loggfunc(starting + " " + success)
        else:
            loggfunc(success)


def main(args: Optional[List[str]] = None):
    ARGS = create_parser().parse_args(args, ArgNamespace())
    CONFIG = Config.from_namespace(ARGS)

    defi: Definition

    if len(CONFIG.definitions) == 1:
        debug("Loaded 1 definition")
    else:
        debug("Loaded {} definitions".format(len(CONFIG.definitions)))

    for file, defi in CONFIG.definitions:
        if defi.name:
            info("Current definition: {} ({})".format(defi.name, file.name))
        else:
            info("Current definition: {}".format(file.name))

        if CONFIG.skip_map:
            debug("Skipping map generation.")
        elif not defi.tasks:
            info("Running PapyrusCs")
            warning("No tasks listed!")
        else:
            info("Running PapyrusCs")
            for command in defi.strung_commands:
                info("  - papyruscs " + " ".join(map(str, command)))
                if not CONFIG.dry_run:
                    result = subprocess.run([CONFIG.papyrus, *command])
                    if result.returncode:
                        raise Exception("An error occured!")

        if CONFIG.skip_sheet:
            debug("Skipping spreadsheet conversion")
        elif defi.spreadsheet:
            with doing_done(info, "Setting playermarkers..."):
                if CONFIG.dry_run:
                    info(defi.spreadsheet)
                else:
                    defi.spreadsheet.write_playermarkers()
        else:
            debug("No spreadsheet entry; skipping.")

        if CONFIG.skip_remote:
            debug("Skipping remote upload")
        elif defi.remote:
            with doing_done(info, "Uploading to remote..."):
                if CONFIG.dry_run:
                    if CONFIG.sheet_only:
                        info("SHEET ONLY: True -> {}".format(defi.remote))
                    else:
                        info(defi.remote)
                elif CONFIG.sheet_only:
                    defi.remote.upload_playersdata()
                else:
                    defi.remote.upload()
        else:
            debug("No remote entry; skipping.")

        if CONFIG.skip_webhook:
            debug("Skipping webhook push")
        elif defi.webhook:
            with doing_done(info, "Pushing to webhook..."):
                if CONFIG.dry_run:
                    info(defi.webhook)
                else:
                    defi.webhook.push()
        else:
            debug("No webhook entry; skipping.")


if __name__ == "__main__":
    initialise_output()
    main()
