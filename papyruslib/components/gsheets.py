import logging
import os
from itertools import repeat
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from googleapiclient.discovery import build
from pydantic import BaseModel

if TYPE_CHECKING:
    from googleapiclient._apis.sheets.v4.resources import (
        SheetsResource,
    )
    from googleapiclient._apis.sheets.v4.schemas import (
        CellData,
        Color,
        Spreadsheet as GSpreadsheet,
    )

from ..bases import Definition, PlayerMarker, Spreadsheet


def hexify(d: "Color") -> str:
    "{red: 1, green: 0.5} -> #ff7f00"
    rgb = d.get("red", 0), d.get("green", 0), d.get("blue", 0)
    return "#{:02x}{:02x}{:02x}".format(*[int(v * 255) for v in rgb])


def get_colour(d: "CellData") -> Optional[str]:
    c = d.get("userEnteredFormat", {}).get("textFormat", {}).get("foregroundColor")
    if c is None:
        return None
    return hexify(c)


def centre_blocks(i: Union[int, float]) -> float:
    if isinstance(i, int):
        return i + 0.5
    return i


def form_location(values: List["CellData"]) -> Tuple[float, float, float]:
    x, y, z = values
    xval = x.get("effectiveValue", {}).get("numberValue")
    if xval is None:
        raise ValueError
    yval = y.get("effectiveValue", {}).get("numberValue", 0)
    zval = z.get("effectiveValue", {}).get("numberValue")
    if zval is None:
        raise ValueError

    return (centre_blocks(xval), yval, centre_blocks(zval))


class DimensionsData(BaseModel):
    id: int = 0
    name: str
    position: str
    check: Optional[str]


class GoogleSheet(Spreadsheet, spec_name="gsheet"):
    id: str
    dimensions: Dict[str, DimensionsData]
    _gsheets: "SheetsResource.SpreadsheetsResource"

    def __init__(self, **data: Any):
        KEY = data.get("key", os.environ.get("GOOGLEAPIKEY"))
        if KEY is None:
            raise Exception(
                "No Google Sheets key found; "
                "set the `GOOGLEAPIKEY` environmental variable"
            )

        service: SheetsResource = build(
            "sheets", "v4", developerKey=KEY, cache_discovery=False
        )

        super().__init__(**data)
        self._gsheets = service.spreadsheets()

    def _fetch_ranges(self, ranges: List[str]) -> "GSpreadsheet":
        return self._gsheets.get(
            spreadsheetId=self.id, ranges=ranges, includeGridData=True
        ).execute()

    def get_playermarkers(
        self, defi: Optional[Definition] = None
    ) -> List[PlayerMarker]:
        "Fetch the array of `PlayerMarker` objects"
        defi = self.get_definition(defi)

        markers: List[PlayerMarker] = []

        for _, dspec in self.dimensions.items():
            ranges = [dspec.name, dspec.position]
            if dspec.check is not None:
                ranges.append(dspec.check)

            data = self._fetch_ranges(ranges)

            # NOTE: assumes all one sheet
            assert len(data.get("sheets", [])) == 1

            ranges = data.get("sheets", [])[0].get("data", [])
            namedata, positiondata, *remaining = ranges
            if remaining:
                (checkdata,) = remaining
            else:
                checkdata = None

            names = [
                o.get("values", [{}])[0].get("formattedValue", "???")
                for o in namedata.get("rowData", [])
            ]
            positions = [
                form_location(r["values"]) if "values" in r else None
                for r in positiondata.get("rowData", [])
            ]
            if checkdata is not None:
                checks = [
                    o["values"][0]
                    .get("effectiveValue", {})
                    .get(
                        "boolValue",
                        bool(o.get("values", [])[0].get("formattedValue", "").strip()),
                    )
                    if "values" in o
                    else False
                    for o in checkdata.get("rowData", [])
                ]
                colours = [
                    get_colour(o.get("values", [])[0]) if "values" in o else None
                    for o in checkdata.get("rowData", [])
                ]
            else:
                checks = repeat(True)
                colours = repeat(None)

            for n, p, ch, c in zip(names, positions, checks, colours):
                if p is None:
                    continue
                m = PlayerMarker(
                    name=n,
                    position=p,
                    visible=ch,
                    dimensionId=dspec.id,
                )
                m.set_uuid_from_name()
                m.set_color(c)
                markers.append(m)

        logging.info("Found {} markers".format(len(markers)))

        return markers
