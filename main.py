#!/usr/bin/env python3
import argparse
from pathlib import Path
from papyruslib.bases import Definition
import subprocess
import colorama
import logging
from logging import debug, info, warning, error
import sys
from contextlib import contextmanager


def existing_path(p):
    p = Path(p)
    assert p.exists()
    return p


parser = argparse.ArgumentParser()

parser.add_argument("-f", "--definition", required=True, type=argparse.FileType("rb"), action="append",
                    help="YAML definition")

parser.add_argument("-p", "--papyrus", default=None, type=existing_path,
                    help="Path to PapyrusCs binary")

parser.add_argument("--dry-run", action="store_true", help="Do nothing")
parser.add_argument("--sheet-only", action="store_true",
                    help="Generate the markers from a sheet *only*")


def initialise_output():
    colorama.init()
    LOGG = Logg()
    logging.basicConfig(
        handlers=[LOGG], level=logging.INFO, format="%(message)s")

    return LOGG


class Logg(logging.StreamHandler):
    _outcolour = colorama.Style.BRIGHT
    _errcolour = colorama.Style.BRIGHT + colorama.Fore.RED
    _outsuffix = colorama.Style.RESET_ALL

    def emit(self, record: logging.LogRecord):
        if record.levelno > 25:
            prefix = self._errcolour
        else:
            prefix = self._outcolour
        suffix = self._outsuffix

        # slightly nabbed from logging.StreamHandler
        try:
            msg = self.format(record)
            self.stream.write(prefix + msg + suffix + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


@contextmanager
def doing_done(
    loggfunc,
    starting: str,
    success: str = "{}done{}.".format(
        colorama.Fore.LIGHTGREEN_EX, colorama.Fore.RESET),
    failure: str = "{}error{}.".format(
        colorama.Fore.RED, colorama.Fore.RESET),
):
    try:
        for handler in logging.getLogger().handlers:
            handler.terminator = ""
            handler.acquire()
        loggfunc(starting + " ")
    finally:
        for handler in logging.getLogger().handlers:
            try:
                handler.terminator = "\n"
                handler.release()
            except Exception:
                pass
    try:
        yield
    except Exception:
        loggfunc(failure)
        raise
    else:
        loggfunc(success)


def main(args=None):
    ARGS = parser.parse_args(args)

    logging.getLogger().setLevel(logging.DEBUG)

    DRY: bool = ARGS.dry_run

    if ARGS.papyrus is None:
        # `this directory`/papyruscs/PapyrusCs(.exe)
        binsuffix = ".exe" if sys.platform.lower().startswith("win") else ""
        PAPYRUS = ((Path(sys.argv[0]).parents[0] / "papyrusbin" / "PapyrusCs")
                   .with_suffix(binsuffix).absolute())
    else:
        PAPYRUS = ARGS.papyrus
    debug(f"PapyrusCs path: {PAPYRUS}")

    DEFINITIONS = [(file, Definition.from_yaml(file))
                   for file in ARGS.definition]
    defi: Definition

    for file, defi in DEFINITIONS:
        defi._cache_all()
    debug("Loaded definitions")

    for file, defi in DEFINITIONS:
        if "name" in defi:
            info("Current definition: {}".format(file.name))
        else:
            info("Current definition: {} ({})".format(
                defi["name"], file.name))

        info("  Running PapyrusCs")
        for command in defi.string_commands():
            info("  - papyruscs " + " ".join(map(str, command)))
            if not DRY:
                result = subprocess.run([PAPYRUS, *command])
                if result.returncode:
                    raise Exception("An error occured!")

        if defi.spreadsheet:
            with doing_done(info, "  Setting playermarkers..."):
                if DRY:
                    print(defi.spreadsheet)
                else:
                    defi.spreadsheet.write_playermarkers()

        if defi.remote:
            with doing_done(info, "  Uploading to remote"):
                if DRY:
                    print(defi.remote)
                else:
                    defi.remote.upload()

        if defi.webhook:
            with doing_done(info, "  Pushing to webhook"):
                if DRY:
                    print(defi.webhook)
                else:
                    defi.webhook.push()


if __name__ == "__main__":
    LOGG = initialise_output()
    main()
