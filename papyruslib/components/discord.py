from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from discord import Embed, SyncWebhook

from ..bases import Definition
from ..bases import Webhook as BaseWebhook

TIMEFILE = "chunks.sqlite"


class DiscordWebhook(BaseWebhook, spec_name="discord"):
    url: str
    link: str

    @staticmethod
    @lru_cache(None)
    def _get_webhook(url: str) -> SyncWebhook:
        return SyncWebhook.from_url(url)

    @property
    def webhook(self) -> SyncWebhook:
        return self._get_webhook(self.url)

    def _construct_embed(self, defi: Definition) -> Embed:
        embed = Embed(title="Map updated!", url=self.link)

        tfile = defi.dest / TIMEFILE
        if tfile.exists():
            embed.timestamp = datetime.fromtimestamp(
                tfile.stat().st_mtime, tz=timezone.utc
            )

        return embed

    def push(self, defi: Optional[Definition] = None) -> None:
        "Calls the Discord webhook"
        defi = self.get_definition(defi)

        embed = self._construct_embed(defi)
        self.webhook.send(embeds=[embed])
        return
