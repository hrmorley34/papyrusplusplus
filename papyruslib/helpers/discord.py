import discord
import requests

from ..bases import Definition, Webhook


class DiscordWebhook(Webhook):
    url: str
    link: str

    def _construct_embed(self, defi: Definition):
        embed = discord.Embed()

        # raise NotImplementedError

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
