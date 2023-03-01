import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from functools import lru_cache
from hashlib import md5
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field, PrivateAttr
from pydantic.types import conlist

cache = lru_cache(maxsize=None)


class PlayerMarker(BaseModel):
    uuid: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    dimensionId: int = Field(...)
    position: Tuple[float, float, float] = Field(...)
    color: Optional[str] = Field(None)
    visible: bool = Field(True)

    class Config:
        extra = "forbid"

    DEFAULT_COLORS: ClassVar[Tuple[str, ...]] = (
        # "#000000",
        "#0000AA",
        "#00AA00",
        "#00AAAA",
        "#AA0000",
        "#AA00AA",
        "#FFAA00",
        # "#AAAAAA",
        # "#555555",
        "#5555FF",
        "#55FF55",
        "#55FFFF",
        "#FF5555",
        "#FF55FF",
        "#FFFF55",
        # "#FFFFFF",
    )

    @property
    def _hash(self) -> bytes:
        value = self.uuid
        if value is None:
            value = self.name
        assert value is not None
        return md5(value.encode("utf-8")).digest()

    @classmethod
    def new(cls) -> "PlayerMarker":
        return cls(
            uuid=str(uuid4()),
            name=None,
            dimensionId=0,
            position=(0.0, 0.0, 0.0),
            color="#ffffff",
            visible=True,
        )

    def set_color(self, color: Optional[str] = None) -> None:
        if color is None:
            color = self.DEFAULT_COLORS[int(self._hash, 16) % len(self.DEFAULT_COLORS)]
        self.color = color

    def set_uuid_from_name(self) -> None:
        assert self.name is not None
        self.uuid = str(UUID(bytes=self._hash))


class SpecedParented(BaseModel):
    specs: ClassVar[Dict[str, Type["SpecedParented"]]]
    spec_base: ClassVar[bool]

    type: str = Field(...)
    _parent: Optional["Definition"] = PrivateAttr(None)

    class Config:
        extra = "forbid"
        underscore_attrs_are_private = True

    def __init_subclass__(
        cls, spec_base: bool = False, spec_name: Optional[str] = None
    ) -> None:
        cls.spec_base = spec_base
        if spec_base:
            cls.specs = {}
        if spec_name is not None:
            cls.specs[spec_name] = cls

        return super().__init_subclass__()

    def __new__(cls, *, type: str, **data: Any) -> "SpecedParented":
        if cls.spec_base:
            if type in cls.specs:
                subcls = cls.specs[type]
                return super().__new__(subcls)
            else:
                raise Exception("Cannot find type {}".format(type))
        else:
            return super().__new__(cls)

    def get_definition(self, defi: Optional["Definition"] = None) -> "Definition":
        if defi is not None:
            return defi
        if self._parent is not None:
            return self._parent
        raise Exception("No definition supplied")

    def set_definition(self, defi: "Definition") -> None:
        self._parent = defi


class Spreadsheet(SpecedParented, ABC, spec_base=True):
    @abstractmethod
    def get_playermarkers(
        self, defi: Optional["Definition"] = None
    ) -> List[PlayerMarker]:
        "Get an array of `PlayerMarker` objects"
        pass

    def write_playermarkers(self, defi: Optional["Definition"] = None) -> None:
        defi = self.get_definition(defi)

        markerdicts = [d.dict() for d in self.get_playermarkers(defi)]
        with open(defi.dest / "map" / "playersData.js", "w") as f:
            f.write(
                "var playersData = " + json.dumps({"players": markerdicts}, indent=2)
            )


class Remote(SpecedParented, ABC, spec_base=True):
    @abstractmethod
    def upload(self, defi: Optional["Definition"] = None) -> None:
        "Run upload task (may call `subprocess.run`)"
        pass

    def upload_playersdata(self, defi: Optional["Definition"] = None) -> None:
        "[Upload all; can be overwritten by subclass]"
        raise NotImplementedError


class Webhook(SpecedParented, ABC, spec_base=True):
    @abstractmethod
    def push(self, defi: Optional["Definition"] = None) -> None:
        "Run push task (may call `requests.post`)"
        pass


_optionstype = Union[List[Any], Dict[str, Any]]


def iterable_to_options(obj: Union[_optionstype, Any]) -> List[str]:
    if isinstance(obj, Mapping):
        olist: List[str] = []
        for k, v in obj.items():
            olist.append(str(k))
            if not any(v is c for c in [None, False, True]):
                olist.append(str(v))
        return olist
    elif isinstance(obj, Sequence):
        return [str(v) for v in obj]
    else:
        raise ValueError()


class OptionsType(List[str]):
    @classmethod
    def __get_validators__(cls):
        yield iterable_to_options

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]):
        # __modify_schema__ should mutate the dict it receives in place,
        # the returned value will be ignored
        field_schema.update(anyOf=[{"type": "array", "items": {}}, {"type": "object"}])


TaskList = conlist(OptionsType, min_items=1)


class Definition(BaseModel):
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

        for obj in (self.spreadsheet, self.remote, self.webhook):
            if obj is not None:
                obj.set_definition(self)

    name: Optional[str]

    world: Path
    dest: Path

    @property
    def base_args(self) -> List[str]:
        return ["--world", str(self.world), "--output", str(self.dest)]

    defaultoptions: OptionsType = Field(default_factory=list)
    validator("defaultoptions", allow_reuse=True)(iterable_to_options)

    tasks: TaskList = Field(...)
    validator("tasks", allow_reuse=True)(iterable_to_options)

    @property
    def strung_commands(self) -> List[List[str]]:
        return [self.base_args + self.defaultoptions + op for op in self.tasks]

    spreadsheet: Optional[Spreadsheet]
    remote: Optional[Remote]
    webhook: Optional[Webhook]

    class Config:
        extra = "forbid"
