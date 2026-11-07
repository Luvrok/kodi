#!/usr/bin/env python3
# drive a running kodi over json-rpc tcp (port 9090, "webserver" on): no
# window focus needed, so the test can run while its real desktop is in
# use. usage: drive.py <method> [json params]
#   drive.py Input.ButtonEvent '{"button":"two","keymap":"keyboard"}'
#   drive.py GUI.GetProperties '{"properties":["currentwindow"]}'
#
# 9090 is kodi's default webserver port; the guisettings.xml sets
# webserver=true (advancedsettings.xml's webserver block didn't take),
# the event client (services.esenabled) is a fallback for actions:
#   kodi-send --host=127.0.0.1 --action="TakeScreenshot"
#
# A modal (a python WindowXML, moviepipe's discover) does not change
# kodi's "currentwindow" in json-rpc: Home stays. Look at the screen or
# use Window props instead.
import socket
import json
import sys


def rpc(method, params=None):
    req = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        req["params"] = params
    s = socket.create_connection(("127.0.0.1", 9090), timeout=10)
    s.settimeout(10)
    s.sendall(json.dumps(req).encode())
    data = b""
    while True:
        try:
            c = s.recv(65536)
        except socket.timeout:
            break
        if not c:
            break
        data += c
        try:
            return json.loads(data.decode())
        except Exception:
            continue
    return {"raw": data.decode()}


if __name__ == "__main__":
    method = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    print(json.dumps(rpc(method, params), ensure_ascii=False))
