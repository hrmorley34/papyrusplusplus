import logging
import shlex
import subprocess
from pathlib import Path
from typing import List, Optional, Union

from pydantic.class_validators import validator

from ..bases import Definition, Remote


class RsyncRemote(Remote, spec_name="rsync"):
    ip: str
    path: str

    @validator("path")
    def _path_validate(cls, path: str):
        if ":" in path:
            raise ValueError("Path cannot contain a colon")
        if '"' in path:
            raise ValueError("Path cannot contain a double quote")
        return path

    def _make_command(self, path: Union[str, Path], destsuffix: str = "") -> List[str]:
        return [
            "rsync",
            # create the directory first, if it doesn't exist
            "--rsync-path",
            f"mkdir -p {shlex.quote(self.path)} && rsync",
            "-rltz",  # recursive, copy symlinks as symlinks, preserve file mod times, compress
            "--delete",  # delete extraneous files in destination
            str(path),
            # the path on the remote computer
            f"{self.ip}::{self.path}/{destsuffix}",
        ]

    def upload(self, defi: Optional[Definition] = None) -> None:
        "Run upload task (calls `subprocess.run` to run `rsync`)"
        defi = self.get_definition(defi)

        # copy the *contents* (trailing slash) of the map folder
        uploadpath = "{}/".format(Path(defi.dest).absolute() / "map")
        command = self._make_command(uploadpath)
        logging.debug(" ".join(map(str, command)))
        result = subprocess.run(
            command, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode:
            raise Exception("Rsync command failed") from None
        return

    def upload_playersdata(self, defi: Optional[Definition] = None) -> None:
        "Run upload task (calls `subprocess.run` to run `rsync`)"
        defi = self.get_definition(defi)

        # copy the playersData file only
        uploadpath = Path(defi.dest).absolute() / "map" / "playersData.js"
        command = self._make_command(uploadpath, "playersData.js")
        logging.debug(" ".join(map(str, command)))
        result = subprocess.run(
            command, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode:
            raise Exception("Rsync command failed") from None
        return
