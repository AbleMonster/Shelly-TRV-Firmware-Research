from pathlib import Path
import hashlib
import struct

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = PROJECT_ROOT / "original" / "SHTRV-01_build.gbl"

data = FIRMWARE.read_bytes()

sha256 = hashlib.sha256(data).hexdigest().upper()

print("Shelly TRV Firmware Inspector")
print("=" * 70)
print(f"Datei:   {FIRMWARE.name}")
print(f"Größe:   {len(data):,} Bytes")
print(f"SHA-256: {sha256}")
print()

print("GBL-Tags")
print("=" * 70)

offset = 0
tag_number = 1

while offset + 8 <= len(data):

    tag_id, length = struct.unpack_from("<II", data, offset)

    print(
        f"{tag_number:02d}: "
        f"Offset 0x{offset:06X} | "
        f"Tag 0x{tag_id:08X} | "
        f"Länge {length:,} Bytes"
    )

    next_offset = offset + 8 + length

    if next_offset <= offset or next_offset > len(data):
        print()
        print("FEHLER: Ungültige Tag-Länge.")
        break

    offset = next_offset
    tag_number += 1

print()
print(f"Parser-Ende: 0x{offset:06X}")
print(f"Dateiende:   0x{len(data):06X}")