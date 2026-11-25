# kodi's json-rpc: its library and a plugin's folder (./actions.py,
# ./collections.py, ./default.py)
import json

import xbmc

from arr import Error


def rpc(method, **params):
    found = json.loads(
        xbmc.executeJSONRPC(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        )
    )
    if "error" in found:
        raise Error(f"kodi: {method}: {found['error'].get('message')}")
    return found.get("result") or {}


def files(directory, media="files", **params):
    # a folder of a plugin or a library, its items as kodi sees them
    return (
        rpc("Files.GetDirectory", directory=directory, media=media, **params).get(
            "files"
        )
        or []
    )
