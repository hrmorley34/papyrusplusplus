from datetime import datetime, timezone
from typing_extensions import Literal
from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field
from pydantic.types import conlist
import requests
from typing import List, Optional

from ..bases import Definition, Webhook as BaseWebhook


TIMEFILE = "chunks.sqlite"


def convert_datetime_to_iso_8601_with_z_suffix(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def transform_to_utc_datetime(dt: datetime) -> datetime:
    return dt.astimezone(tz=timezone.utc)


class DiscordBaseModel(BaseModel):
    class Config:
        json_encoders = {datetime: convert_datetime_to_iso_8601_with_z_suffix}


class EmbedThumbnail(DiscordBaseModel):
    url: str
    proxy_url: Optional[str]
    height: Optional[int]
    width: Optional[int]


class EmbedVideo(DiscordBaseModel):
    url: Optional[str]
    proxy_url: Optional[str]
    height: Optional[int]
    width: Optional[int]


class EmbedImage(DiscordBaseModel):
    url: str
    proxy_url: Optional[str]
    height: Optional[int]
    width: Optional[int]


class EmbedProvider(DiscordBaseModel):
    name: Optional[str]
    url: Optional[str]


class EmbedAuthor(DiscordBaseModel):
    name: str
    url: Optional[str]
    icon_url: Optional[str]
    proxy_icon_url: Optional[str]


class EmbedFooter(DiscordBaseModel):
    text: str
    icon_url: Optional[str]
    proxy_icon_url: Optional[str]


class EmbedField(DiscordBaseModel):
    name: str
    value: str
    inline: Optional[bool]


class Embed(DiscordBaseModel):
    title: Optional[str]
    # type: Optional[str]
    type: Literal["rich"] = "rich"
    description: Optional[str]
    url: Optional[str]
    timestamp: Optional[datetime]
    validator("timestamp", allow_reuse=True)(transform_to_utc_datetime)
    color: Optional[int]
    footer: Optional[EmbedFooter]
    image: Optional[EmbedImage]
    thumbnail: Optional[EmbedThumbnail]
    # video: Optional[EmbedVideo]
    # provider: Optional[EmbedProvider]
    author: Optional[EmbedAuthor]
    fields: Optional[List[EmbedField]]


embedlist = conlist(Embed, max_items=10)


class WebhookMesage(DiscordBaseModel, extra="allow"):
    content: str
    # username: Optional[str]
    # avatar_url: Optional[str]
    tts: bool
    embeds: embedlist = Field(default_factory=list)
    # allowed_mentions: ...
    # components: ...
    # files: List[...]
    # payload_json: str
    # attachments: ...


class WebhookReplyMessage(DiscordBaseModel, extra="allow"):
    id: str
    type: int
    content: str
    channel_id: str
    # author: ...
    # attachments: List[...]
    embeds: List[Embed]
    # mentions: List[...]
    # mention_roles: List[...]
    pinned: bool
    mention_everyone: bool
    tts: bool
    timestamp: datetime
    edited_timestamp: Optional[datetime]
    flags: int
    # components: List[...]
    webhook_id: str


class Webhook:
    url: str
    last_message: Optional[WebhookReplyMessage]

    def __init__(self, url: str) -> None:
        self.url = url
        self.last_message = None

    def execute(self, message: WebhookMesage) -> WebhookReplyMessage:
        r = requests.post(
            self.url,
            json=message.dict(exclude_none=True),
            params=dict(wait=True),
        )
        r.raise_for_status()
        self.last_message = WebhookReplyMessage.parse_obj(r.json())
        return self.last_message

    def edit(self, message: WebhookMesage) -> WebhookReplyMessage:
        assert self.last_message is not None

        r = requests.patch(
            self.url + "/messages/" + self.last_message.id,
            json=message.dict(exclude_none=True),
            params=dict(wait=True),
        )
        r.raise_for_status()
        self.last_message = WebhookReplyMessage.parse_obj(r.json())
        return self.last_message


class DiscordWebhook(BaseWebhook, spec_name="discord"):
    url: str
    link: str

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
        message = WebhookMesage(embeds=[embed])
        Webhook(self.url).execute(message)
        return
