from pathlib import Path
import subprocess

from ..bases import Remote, Definition


class RsyncRemote(Remote):
    ip: str
    path: str

    def _make_command(self, source: Path) -> list:
        return [
            "rsync",
            # create the directory first, if it doesn't exist
            "--rsync-path", f"mkdir -p \"{self.path}\" && rsync",
            "-azrlt",  # archive, compress, recursive, symlinks, preserve file mod times
            # copy the *contents* (trailing slash) of the map folder
            "{}/".format(Path(source) / "map"),
            f"{self.ip}:{self.path}",  # the path on the remote computer
        ]

    def upload(self, defi: Definition = None) -> subprocess.CompletedProcess:
        " Run upload task (calls `subprocess.run` to run `rsync`) "
        defi = self._parent or defi
        assert defi

        command = self._make_command(defi.dest)
        result = subprocess.run(command, stdin=None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise Exception("Rsync command failed") from None
        return result


Remote.specs["rsync"] = RsyncRemote
