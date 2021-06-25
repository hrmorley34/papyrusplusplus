from abc import ABC, abstractmethod
from uuid import UUID, uuid4
from hashlib import md5
from typing import Tuple, Union, List
from collections.abc import Mapping, MutableMapping
import yaml
import json
from pathlib import Path

try:
    from functools import cache
except ImportError:
    from functools import lru_cache
    cache = lru_cache(maxsize=None)


_optionstype = Union[list, dict]


class DictObject(MutableMapping):
    _data: dict
    _hash: int

    def __init__(self, data: dict):
        self._data = data
        self._hash = int(uuid4())

    def __hash__(self):
        return getattr(self, "_hash", int(uuid4()))

    def __repr__(self):
        return type(self).__name__ + repr(self._data)

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(type(self).__name__ + "{...}")
        else:
            with p.group(2, type(self).__name__ + "{", "}"):
                for idx, (key, item) in enumerate(self._data.items()):
                    if idx:
                        p.text(",")
                        p.breakable()
                    else:
                        p.breakable("")
                    p.pretty(key)
                    p.text(": ")
                    p.pretty(item)

    def __getattr__(self, key):
        try:
            return object.__getattr__(self, key)
        except AttributeError:
            try:
                return self[key]
            except KeyError:
                pass
            raise  # reraise AttributeError

    def __setattr__(self, key, value):
        if key[0] == "_":
            return object.__setattr__(self, key, value)
        self[key] = value

    def __delattr__(self, key):
        if key[0] == "_":
            return object.__delattr__(self, key)
        del self[key]

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __eq__(self, obj):
        if isinstance(obj, DictObject):
            return self._data == obj._data
        elif self._data == obj:
            return True
        return NotImplemented

    def __dir__(self):
        return set(object.__dir__(self)) | set(self._data.keys())

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def to_dict(self):
        return self._data


class PlayerMarker(DictObject):
    uuid: str
    name: str
    dimensionId: int
    position: Tuple[float, float, float]
    color: str
    visible: bool

    DEFAULT_COLORS = (
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
    def _hash(self):
        return md5((self.name or self.uuid).encode("utf-8")).hexdigest()

    def __init__(self, data: dict = None):
        if data is None:
            data = {
                "uuid": str(uuid4()),
                "name": None,
                "dimensionId": 0,
                "position": (0, 0, 0),
                "color": "#ffffff",
                "visible": True,
            }
        self._data = data

    def set_color(self, color=None):
        if color is None:
            color = self.DEFAULT_COLORS[int(
                self._hash, 16) % len(self.DEFAULT_COLORS)]
        self.color = color

    def set_uuid_from_name(self):
        self.uuid = str(UUID(self._hash))


class _SpecedParented(DictObject, ABC):
    specs: dict
    type: str

    def __new__(cls, data: dict, *args, **kwargs):
        if cls is Spreadsheet:
            if data["type"] in cls.specs:
                subcls = cls.specs[data["type"]]
                return object.__new__(subcls)
            else:
                raise Exception("Cannot find type {}".format(data["type"]))
        else:
            return object.__new__(cls)

    def __init__(self, data: dict, parent: "Definition" = None):
        self._data = data
        self._hash = int(uuid4())
        self._parent = parent


class Spreadsheet(_SpecedParented):
    specs: dict = {}

    def __new__(cls, data: dict, *args, **kwargs):
        if cls is Spreadsheet:
            if data["type"] in cls.specs:
                subcls = cls.specs[data["type"]]
                return object.__new__(subcls)
            else:
                raise Exception("Cannot find type {}".format(data["type"]))
        else:
            return object.__new__(cls)

    @abstractmethod
    def get_playermarkers(self, defi: "Definition" = None) -> List[PlayerMarker]:
        " Get an array of `PlayerMarker` objects "
        pass

    def write_playermarkers(self, defi: "Definition" = None):
        defi = self._parent or defi
        assert defi

        markerdicts = [d.to_dict() for d in self.get_playermarkers()]
        with open(defi.dest / "map" / "playersData.js", "w") as f:
            f.write("var playersData = "
                    + json.dumps({"players": markerdicts}, indent=2))


class Remote(_SpecedParented):
    specs: dict = {}

    def __new__(cls, data: dict, *args, **kwargs):
        if cls is Remote:
            if data["type"] in cls.specs:
                subcls = cls.specs[data["type"]]
                return object.__new__(subcls)
            else:
                raise Exception("Cannot find type {}".format(data["type"]))
        else:
            return object.__new__(cls)

    @abstractmethod
    def upload(self, defi: "Definition" = None):
        " Run upload task (may call `subprocess.run`) "
        pass

    def upload_playersdata(self, defi: "Definition" = None):
        " [Upload all; can be overwritten by subclass] "
        return self.upload()


class Webhook(_SpecedParented):
    specs: dict = {}

    def __new__(cls, data: dict, *args, **kwargs):
        if cls is Webhook:
            if data["type"] in cls.specs:
                subcls = cls.specs[data["type"]]
                return object.__new__(subcls)
            else:
                raise Exception("Cannot find type {}".format(data["type"]))
        else:
            return object.__new__(cls)

    @abstractmethod
    def push(self, defi: "Definition" = None):
        " Run push task (may call `requests.post`) "
        pass


def iterable_to_options(obj: _optionstype) -> list:
    if isinstance(obj, Mapping):
        olist = []
        for k, v in obj.items():
            olist.append(str(k))
            if not any(v is c for c in [None, False, True]):
                olist.append(str(v))
        return olist
    return [str(v) for v in obj]


class Definition(DictObject):
    name: str

    world: Path

    @property
    def world(self):
        return Path(self["world"])

    dest: Path

    @property
    def dest(self):
        return Path(self["dest"])

    defaultoptions: _optionstype
    tasks: List[_optionstype]

    def string_commands(self) -> List[List[str]]:
        start = ["--world", self.world, "--output", self.dest]
        start += iterable_to_options(self.get("defaultoptions", {}))
        return [start + iterable_to_options(op) for op in self["tasks"]]

    spreadsheet: Spreadsheet

    @property
    @cache
    def spreadsheet(self) -> Spreadsheet:
        return Spreadsheet(self["spreadsheet"], parent=self) if self.get("spreadsheet") else None

    remote: Remote

    @property
    @cache
    def remote(self) -> Remote:
        return Remote(self["remote"], parent=self) if self.get("remote") else None

    webhook: Webhook

    @property
    @cache
    def webhook(self) -> Webhook:
        return Webhook(self["webhook"], parent=self) if self.get("webhook") else None

    @classmethod
    def from_yaml(cls, yamltext: str, loader=yaml.SafeLoader):
        return cls(yaml.load(yamltext, Loader=loader))

    def _cache_all(self):
        # get each one, to cache it
        self.spreadsheet, self.remote, self.webhook
