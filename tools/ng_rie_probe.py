#!/usr/bin/env python3
"""Read-only bring-up tool for the Mettler Toledo NG-RIE AutoShelf board.

Link: RS-485, 9600 baud, 8N1 (FTDI USB-RS485-WE cable or any USB/RS-485 adapter).

Usage:
    pip install pyserial
    python ng_rie_probe.py COM5 info
    python ng_rie_probe.py COM5 watch --channels 2 --period 0.2
    python ng_rie_probe.py /dev/ttyUSB0 watch --verbose

Only read commands are sent (A, V, 1, Q, O, T): the tool never changes the
board configuration, its calibration or its zero.
"""
import argparse
import statistics
import sys
import time
from collections import deque

HEAD = 0xF2
END = 0xF3
PADS = "0123456789AB"
CHANNEL_COUNTS = "123456789ABC"


class BoardError(Exception):
    pass


def checksum(body: bytes) -> int:
    value = 0
    for byte in body:
        value ^= byte
    return value


def build_frame(payload: bytes) -> bytes:
    # L counts the bytes after itself: payload + checksum + END.
    body = bytes([len(payload) + 2]) + payload
    return bytes([HEAD]) + body + bytes([checksum(body), END])


def read_frame(port, timeout: float, verbose: bool = False):
    """Return the payload of the next valid frame, or None on timeout.

    The protocol has no byte stuffing (the checksum may be 0xF2/0xF3),
    so the frame is delimited by its length byte, not by scanning for END.
    """
    deadline = time.monotonic() + timeout

    def next_byte():
        while time.monotonic() < deadline:
            data = port.read(1)
            if data:
                return data[0]
        return None

    while True:
        byte = next_byte()
        if byte is None:
            return None
        if byte != HEAD:
            continue
        length = next_byte()
        if length is None:
            return None
        if length < 3:
            continue
        rest = bytearray()
        while len(rest) < length:
            byte = next_byte()
            if byte is None:
                return None
            rest.append(byte)
        payload = bytes(rest[:-2])
        frame = bytes([HEAD, length]) + bytes(rest)
        if rest[-1] != END or rest[-2] != checksum(bytes([length]) + payload):
            print(f"  ! invalid frame ignored: {frame.hex(' ')}", file=sys.stderr)
            continue
        if verbose:
            print(f"  RX {frame.hex(' ')}  {payload!r}")
        return payload


def is_power_up(response: bytes) -> bool:
    return response[1:2] == b"E" and response.endswith(b"PW")


class Board:
    def __init__(self, port, timeout: float = 0.3, verbose: bool = False):
        self.port = port
        self.timeout = timeout
        self.verbose = verbose
        self.board_id = b""

    def transact(self, payload: bytes, retries: int = 3):
        for _ in range(retries):
            self.port.reset_input_buffer()
            frame = build_frame(payload)
            if self.verbose:
                print(f"  TX {frame.hex(' ')}  {payload!r}")
            self.port.write(frame)
            response = read_frame(self.port, self.timeout, self.verbose)
            if response == payload:
                # Some adapters echo what they transmit on the shared pair.
                response = read_frame(self.port, self.timeout, self.verbose)
            if response is None:
                continue
            if is_power_up(response):
                print("  board is powering up (PW), retrying in 1 s")
                time.sleep(1)
                continue
            return response
        return None

    def discover(self, wait_s: float = 10.0) -> bytes:
        # A freshly powered board may stay silent for a few seconds (bootloader).
        deadline = time.monotonic() + wait_s
        response = self.transact(b"A")
        while response is None and time.monotonic() < deadline:
            print("  no answer yet, retrying (check 12 V, A/B wires and COM port)")
            response = self.transact(b"A")
        if response is None or response[0:1] != b"a" or len(response) < 5:
            raise BoardError(f"no valid answer to 'A' after {wait_s:.0f} s (got {response!r})")
        self.board_id = response[1:5]
        return self.board_id

    def command(self, letter: bytes, extra: bytes = b""):
        return self.transact(letter + self.board_id + extra)

    def channel_weights(self, count: int):
        response = self.command(b"T", CHANNEL_COUNTS[count - 1].encode())
        if response is None:
            raise BoardError("no answer to 'T'")
        return parse_weights(response)


def parse_weights(payload: bytes):
    """Parse 't' + N + N fields of 10 chars: sign, 8-char weight, status."""
    if payload[0:1] != b"t":
        raise BoardError(f"unexpected answer {payload!r}")
    if payload[1:2] == b"E":
        raise BoardError(f"board error {payload[2:].decode('ascii', 'replace')}")
    count = int(chr(payload[1]), 16)
    data = payload[2:]
    # The spec draws '|' between fields; accept them if the board really sends them.
    field_size = 11 if len(data) == count * 11 else 10
    fields = [data[i * field_size:i * field_size + 10] for i in range(count)]
    return [parse_weight_field(field.decode("ascii", "replace")) for field in fields]


def parse_weight_field(field: str):
    """Return (value or None, status) where status is OK, M, C, I or E<n>."""
    sign, digits, status = field[0], field[1:9], field[9:10]
    if sign == "E":
        return None, "E" + digits.strip()
    try:
        value = float(digits)
    except ValueError:
        return None, f"?{field!r}"
    return (-value if sign == "-" else value), (status.strip() or "OK")


INFO_QUERIES = [
    ("Firmware version", b"V", b""),
    ("Serial number", b"1", b"1"),
    ("Alias name", b"1", b"3"),
    ("Channel counts", b"1", b"4"),
    ("Model (shelf mode)", b"Q", b""),
    ("Calibration weight (shelf mode)", b"O", b""),
]


def print_info(board: Board):
    print(f"Board ID: {board.board_id!r} (hex {board.board_id.hex(' ')})")
    queries = list(INFO_QUERIES)
    for pad in PADS:
        queries.append((f"Pad {pad} config (divisions, capacity/div)", b"Q", b"#" + pad.encode()))
        queries.append((f"Pad {pad} calibration weight", b"O", b"#" + pad.encode()))
    for label, letter, extra in queries:
        response = board.command(letter, extra)
        shown = "no answer" if response is None else f"{response!r}"
        print(f"{label:45} {shown}")


def watch(board: Board, channels: int, period: float):
    totals = deque(maxlen=25)
    header = "  ".join(f"ch{i:<13}" for i in range(channels))
    print(f"time(s)  {header}  sum        stdev(last 25)")
    start = time.monotonic()
    while True:
        cycle_start = time.monotonic()
        elapsed = cycle_start - start
        try:
            readings = board.channel_weights(channels)
        except BoardError as error:
            print(f"{elapsed:7.1f}  {error}")
        else:
            cells = "  ".join(f"{value if value is not None else '-':>9} {status:<5}" for value, status in readings)
            values = [value for value, _ in readings if value is not None]
            total = sum(values) if len(values) == len(readings) else None
            if total is not None:
                totals.append(total)
            spread = f"{statistics.pstdev(totals):.4f}" if len(totals) >= 2 else "-"
            total_text = f"{total:9.3f}" if total is not None else "        -"
            print(f"{elapsed:7.1f}  {cells}  {total_text}  {spread}")
        time.sleep(max(0.0, period - (time.monotonic() - cycle_start)))


def main():
    parser = argparse.ArgumentParser(description="Read-only probe for the Mettler Toledo NG-RIE board")
    parser.add_argument("port", help="serial port, e.g. COM5 or /dev/ttyUSB0")
    parser.add_argument("action", choices=["info", "watch"])
    parser.add_argument("--channels", type=int, default=2, help="channels read by 'watch' (1-12)")
    parser.add_argument("--period", type=float, default=0.2, help="polling period in seconds")
    parser.add_argument("--verbose", action="store_true", help="print raw frames")
    args = parser.parse_args()

    import serial  # pyserial

    port = serial.Serial(args.port, 9600, bytesize=8, parity="N", stopbits=1, timeout=0.05)
    board = Board(port, verbose=args.verbose)
    try:
        print(f"Board found, ID {board.discover()!r}")
        if args.action == "info":
            print_info(board)
        else:
            watch(board, args.channels, args.period)
    except BoardError as error:
        print(f"Error: {error}")
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        port.close()


if __name__ == "__main__":
    main()
