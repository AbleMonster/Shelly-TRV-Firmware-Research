from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIRMWARE_NAME = "SHTRV-01_build_2.2.4_beacon_patch.gbl"

HOST = "0.0.0.0"
PORT = 80
CHUNK_SIZE = 16 * 1024


class ShellyOTAHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        print(
            f"[HTTP] {self.client_address[0]}:{self.client_address[1]} "
            f"- {format % args}",
            flush=True,
        )

    def do_GET(self):
        print("\n" + "=" * 70, flush=True)
        print("NEW GET REQUEST", flush=True)
        print("=" * 70, flush=True)

        print(f"Client:  {self.client_address[0]}:{self.client_address[1]}", flush=True)
        print(f"Request: GET {self.path}", flush=True)

        print("\nRequest headers:", flush=True)
        for key, value in self.headers.items():
            print(f"  {key}: {value}", flush=True)

        requested_path = self.path.split("?", 1)[0]

        if requested_path != f"/{FIRMWARE_NAME}":
            self.send_error(404, "Firmware not found")
            return

        firmware = PROJECT_ROOT / FIRMWARE_NAME

        if not firmware.exists():
            self.send_error(404, "Firmware not found")
            return

        file_size = firmware.stat().st_size

        # Standard: komplette Datei
        start = 0
        end = file_size - 1

        range_header = self.headers.get("Range")

        if range_header:
            print(f"\nRange requested: {range_header}", flush=True)

            try:
                unit, value = range_header.split("=", 1)

                if unit.strip().lower() != "bytes":
                    raise ValueError("Unsupported range unit")

                start_text, end_text = value.split("-", 1)

                if start_text:
                    start = int(start_text)

                if end_text:
                    end = int(end_text)

                if start < 0 or start >= file_size:
                    raise ValueError("Range start outside file")

                if end >= file_size:
                    end = file_size - 1

                if end < start:
                    raise ValueError("Invalid range")

            except ValueError as exc:
                print(f"[ERROR] Invalid Range header: {exc}", flush=True)

                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Connection", "close")
                self.end_headers()
                return

        content_length = end - start + 1

        print(f"\nFirmware: {firmware}", flush=True)
        print(f"File size: {file_size:,} bytes", flush=True)
        print(f"Sending:   {start:,}-{end:,}", flush=True)
        print(f"Length:    {content_length:,} bytes", flush=True)

        if range_header:
            self.send_response(206)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header(
                "Content-Range",
                f"bytes {start}-{end}/{file_size}"
            )
            self.send_header("Content-Length", str(content_length))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(file_size))

        self.send_header("Connection", "close")
        self.end_headers()

        print("\nResponse:", flush=True)

        if range_header:
            print("  HTTP/1.1 206 Partial Content", flush=True)
            print(f"  Content-Range: bytes {start}-{end}/{file_size}", flush=True)
        else:
            print("  HTTP/1.1 200 OK", flush=True)

        print(f"  Content-Length: {content_length}", flush=True)
        print("  Accept-Ranges: bytes", flush=True)
        print("  Connection: close", flush=True)

        sent = 0
        start_time = time.monotonic()
        next_report = 5

        print("\nTransfer started...", flush=True)

        try:
            with firmware.open("rb") as f:
                f.seek(start)

                remaining = content_length

                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))

                    if not chunk:
                        break

                    self.wfile.write(chunk)
                    self.wfile.flush()

                    sent += len(chunk)
                    remaining -= len(chunk)

                    percent = (sent * 100) / content_length

                    if percent >= next_report or remaining == 0:
                        elapsed = time.monotonic() - start_time

                        print(
                            f"  {sent:>10,} / {content_length:,} bytes "
                            f"({percent:6.2f} %) "
                            f"after {elapsed:.2f} s",
                            flush=True,
                        )

                        while next_report <= percent:
                            next_report += 5

        except (
            BrokenPipeError,
            ConnectionResetError,
            ConnectionAbortedError,
            TimeoutError,
            OSError,
        ) as exc:

            elapsed = time.monotonic() - start_time

            print("\n!!! TRANSFER INTERRUPTED !!!", flush=True)
            print(f"Exception: {type(exc).__name__}: {exc}", flush=True)
            print(f"Bytes sent: {sent:,} / {content_length:,}", flush=True)
            print(f"Progress:   {sent * 100 / content_length:.2f} %", flush=True)
            print(f"Duration:   {elapsed:.2f} s", flush=True)
            print("=" * 70, flush=True)
            return

        elapsed = time.monotonic() - start_time

        print("\n" + "=" * 70, flush=True)

        if sent == content_length:
            print("TRANSFER COMPLETED", flush=True)
        else:
            print("TRANSFER ENDED WITH WRONG BYTE COUNT", flush=True)

        print(f"Bytes sent: {sent:,} / {content_length:,}", flush=True)
        print(f"Duration:   {elapsed:.2f} s", flush=True)
        print("=" * 70, flush=True)


if __name__ == "__main__":
    firmware = PROJECT_ROOT / FIRMWARE_NAME

    if not firmware.exists():
        raise FileNotFoundError(f"Firmware not found: {firmware}")

    print("Shelly TRV OTA diagnostic server")
    print(f"Firmware: {firmware}")
    print(f"Size:     {firmware.stat().st_size:,} bytes")
    print(f"Listening on {HOST}:{PORT}")
    print(f"OTA file: /{FIRMWARE_NAME}")
    print()
    print("Waiting for Shelly TRV...")

    server = HTTPServer((HOST, PORT), ShellyOTAHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()