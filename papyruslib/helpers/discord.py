from discord import Embed
import requests
from datetime import datetime

from ..bases import Definition, Webhook


TIMEFILE = "chunks.sqlite"


class DiscordWebhook(Webhook):
    url: str
    link: str

    def _construct_embed(self, defi: Definition) -> Embed:
        embed = Embed(title="Map updated!", url=self.link)

        tfile = (defi.dest / TIMEFILE)
        if tfile.exists():
            embed.timestamp = datetime.fromtimestamp(tfile.stat().st_mtime)

        return embed

    def push(self, defi: Definition = None) -> requests.Response:
        " Calls the Discord webhook "
        defi = self._parent or defi
        assert defi

        embed = self._construct_embed(defi)

        r = requests.post(self.url, json={"embeds": [embed.to_dict()]})
        r.raise_for_status()
        return r


Webhook.specs["discord"] = DiscordWebhook
