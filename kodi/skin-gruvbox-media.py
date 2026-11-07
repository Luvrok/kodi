# the skin's own textures, drawn here (no binaries in git): a white 1x1
# png that every fill, hairline and focus frame tints with colordiffuse.
# skin-gruvbox-media.py MEDIADIR
import os
import struct
import sys
import zlib


def chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def png(path, rows):
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", len(rows[0]) // 4, len(rows), 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(b"".join(b"\0" + row for row in rows))))
        f.write(chunk(b"IEND", b""))


out = sys.argv[1]
os.makedirs(os.path.join(out, "common"), exist_ok=True)
png(os.path.join(out, "common", "white.png"), [b"\xff\xff\xff\xff"])
