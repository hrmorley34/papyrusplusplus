from pathlib import Path
import subprocess
import logging

from ..bases import Remote, Definition


class RsyncRemote(Remote):
    ip: str
    path: str

    def _make_command(self, path: str, destsuffix: str = "") -> list:
        return [
            "rsync",
            # create the directory first, if it doesn't exist
            "--rsync-path", f"mkdir -p \"{self.path}\" && rsync",
            "-azrlt",  # archive, compress, recursive, symlinks, preserve file mod times
            "--delete",  # delete extraneous files in destination
            path,
            # the path on the remote computer
            f"{self.ip}:{self.path}/{destsuffix}",
        ]

    def upload(self, defi: Definition = None) -> subprocess.CompletedProcess:
        " Run upload task (calls `subprocess.run` to run `rsync`) "
        defi = self._parent or defi
        assert defi

        # copy the *contents* (trailing slash) of the map folder
        uplpath = "{}/".format(Path(defi.dest).absolute() / "map")
        command = self._make_command(uplpath)
        logging.debug(" ".join(map(str, command)))
        result = subprocess.run(command, stdin=None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise Exception("Rsync command failed") from None
        return result

    def upload_playersdata(self, defi: Definition = None) -> subprocess.CompletedProcess:
        " Run upload task (calls `subprocess.run` to run `rsync`) "
        defi = self._parent or defi
        assert defi

        # copy the playersData file only
        uplpath = Path(defi.dest).absolute() / "map" / "playersData.js"
        command = self._make_command(uplpath, "playersData.js")
        logging.debug(" ".join(map(str, command)))
        result = subprocess.run(command, stdin=None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise Exception("Rsync command failed") from None
        return result


Remote.specs["rsync"] = RsyncRemote
