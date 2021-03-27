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
# parser.add_argument("--sheet-only", action="store_true",
#                     help="Generate the markers from a sheet *only*")

parser.add_argument("--skip-map", action="store_true",
                    help="Skip map generation")
parser.add_argument("--skip-sheet", action="store_true",
                    help="Skip player markers generation")
parser.add_argument("--skip-remote", action="store_true",
                    help="Skip remote upload")
parser.add_argument("--skip-webhook", action="store_true",
                    help="Skip webhook push")


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
    _doingdone_active = False

    def emit(self, record: logging.LogRecord):
        if record.levelno > 25:
            prefix = self._errcolour
        else:
            prefix = self._outcolour
        suffix = self._outsuffix

        if self._doingdone_active:
            self._doingdone_active = False
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
            if handler._doingdone_active:
                handler._doingdone_active = False
            else:
                printagain = True
    return printagain


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
            finally:
                if isinstance(handler, Logg):
                    handler._doingdone_active = True
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


def main(args=None):
    ARGS = parser.parse_args(args)

    logging.getLogger().setLevel(logging.INFO)

    DRY: bool = ARGS.dry_run

    if ARGS.papyrus is None:
        # `this directory`/papyruscs/PapyrusCs(.exe)
        binsuffix = ".exe" if sys.platform.lower().startswith("win") else ""
        PAPYRUS = ((Path(sys.argv[0]).parents[0] / "papyrusbin" / "PapyrusCs")
                   .with_suffix(binsuffix).absolute())
    else:
        PAPYRUS = ARGS.papyrus
    debug(f"PapyrusCs path: {PAPYRUS}")

    SKIP_GEN = ARGS.skip_map
    SKIP_SPREADSHEET = ARGS.skip_sheet
    SKIP_REMOTE = ARGS.skip_remote
    SKIP_WEBHOOK = ARGS.skip_webhook

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

        if SKIP_GEN:
            debug("Skipping map generation.")
        elif not defi.tasks:
            info("Running PapyrusCs")
            warning("No tasks listed!")
        else:
            info("Running PapyrusCs")
            for command in defi.string_commands():
                info("  - papyruscs " + " ".join(map(str, command)))
                if not DRY:
                    result = subprocess.run([PAPYRUS, *command])
                    if result.returncode:
                        raise Exception("An error occured!")

        if SKIP_SPREADSHEET:
            debug("Skipping spreadsheet conversion")
        elif defi.spreadsheet:
            with doing_done(info, "Setting playermarkers..."):
                if DRY:
                    print(defi.spreadsheet)
                else:
                    defi.spreadsheet.write_playermarkers()
        else:
            debug("No spreadsheet entry; skipping.")

        if SKIP_REMOTE:
            debug("Skipping remote upload")
        elif defi.remote:
            with doing_done(info, "  Uploading to remote..."):
                if DRY:
                    print(defi.remote)
                else:
                    defi.remote.upload()
        else:
            debug("No remote entry; skipping.")

        if SKIP_WEBHOOK:
            debug("Skipping webhook push")
        elif defi.webhook:
            with doing_done(info, "  Pushing to webhook..."):
                if DRY:
                    print(defi.webhook)
                else:
                    defi.webhook.push()
        else:
            debug("No webhook entry; skipping.")


if __name__ == "__main__":
    LOGG = initialise_output()
    main()
