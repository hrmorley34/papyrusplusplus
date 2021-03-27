from itertools import repeat
import os
from googleapiclient.discovery import build
from typing import List

from ..bases import _SpecedParented, Spreadsheet, PlayerMarker, Definition


def hexify(d: dict) -> str:
    " {red: 1, green: 0.5} -> #ff7f00 "
    rgb = d.get("red", 0), d.get("green", 0), d.get("blue", 0)
    return "#{:02x}{:02x}{:02x}".format(*[int(v*255) for v in rgb])


def get_colour(d: dict):
    try:
        return hexify(d["userEnteredFormat"]["textFormat"]["foregroundColor"])
    except KeyError:
        return None


def form_location(values: list) -> list:
    x, y, z = values
    xval = x["effectiveValue"]["numberValue"]
    yval = y.get("effectiveValue", {}).get("numberValue", 0)
    zval = z["effectiveValue"]["numberValue"]

    return [xval, yval, zval]


class GoogleSheet(Spreadsheet):
    def __init__(self, data: dict, parent: Definition = None):
        KEY = data.get("key", os.environ.get("GOOGLEAPIKEY"))
        if KEY is None:
            raise Exception("No Google Sheets key found; "
                            "set the `GOOGLEAPIKEY` environmental variable")

        service = build("sheets", "v4", developerKey=KEY, cache_discovery=False)

        _SpecedParented.__init__(self, data, parent=parent)
        self._gsheets = service.spreadsheets()

    def _fetch_ranges(self, ranges: list) -> dict:
        return self._gsheets.get(spreadsheetId=self.id, ranges=ranges, includeGridData=True).execute()

    def get_playermarkers(self, defi: Definition = None) -> List[PlayerMarker]:
        " Fetch the array of `PlayerMarker` objects "
        defi = self._parent or defi
        assert defi

        markers = []

        for dname, dspec in self["dimensions"].items():
            ranges = [dspec["name"], dspec["position"]]
            if "check" in dspec:
                ranges.append(dspec["check"])

            data = self._fetch_ranges(ranges)

            # NOTE: assumes all one sheet
            names = [o.get("values", [{}])[0].get("formattedValue", "???")
                     for o in data["sheets"][0]["data"][0]["rowData"]]
            positions = [form_location(r["values"]) if "values" in r else None
                         for r in data["sheets"][0]["data"][1]["rowData"]]
            if "check" in dspec:
                checks = [o["values"][0]["effectiveValue"].get("boolValue", bool(o["values"][0]["formattedValue"].strip()))
                          if "values" in o else False
                          for o in data["sheets"][0]["data"][2]["rowData"]]
                colours = [get_colour(o["values"][0]) if "values" in o else None
                           for o in data["sheets"][0]["data"][2]["rowData"]]
            else:
                checks = repeat(True)
                colours = repeat(None)

            for n, p, ch, c in zip(names, positions, checks, colours):
                if p is None:
                    continue
                m = PlayerMarker()
                m.name, m.position, m.visible = n, p, ch
                m.dimensionId = dspec.get("id", 0)
                m.set_uuid_from_name()
                m.set_color(c)
                markers.append(m)
        return markers


Spreadsheet.specs["gsheet"] = GoogleSheet
