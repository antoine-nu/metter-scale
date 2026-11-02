#!/usr/bin/env python3
"""PC simulation of the bathroom-scale firmware, fed by the real NG-RIE board.

The firmware logic lives in scale_logic.py; this file only does the I/O that
the Arduino will do differently: RS-485 through the USB cable, a drawing of the
4-digit display in the terminal, and scale_eeprom.json for the EEPROM.

    python scale_firmware_sim.py COM7            # fixed display drawn in the terminal
    python scale_firmware_sim.py COM7 --plain    # one line per display change (to copy-paste)

Read-only for the board. The scale switches itself off after 30 s at 0: run the
program again to "wake it up" (the kick on the real scale).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from ng_rie_probe import Board, BoardError
from scale_logic import POLL_PERIOD_S, ScaleFirmware

WEIGHING_PAD_COUNT = 2

# Segments a..g of each character, a 7-segment display drawn on 3 text lines:
#    _        a
#   |_|      f g b
#   |_|.     e d c   dp
SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg",
    "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg", " ": "", "-": "g",
    "A": "abcefg", "b": "cdefg", "C": "adef", "c": "deg", "d": "bcdeg", "E": "adefg",
    "F": "aefg", "H": "bcefg", "h": "cefg", "I": "ef", "J": "bcde", "L": "def",
    "n": "ceg", "o": "cdeg", "O": "abcdef", "P": "abefg", "r": "eg", "S": "acdfg",
    "t": "defg", "U": "bcdef", "u": "cde", "y": "bcdfg",
}


def display_cells(text: str):
    """Split ' 67.4' into 4 (character, decimal point) cells."""
    cells = []
    for char in text:
        if char == "." and cells:
            cells[-1] = (cells[-1][0], True)
        else:
            cells.append((char, False))
    return cells


def draw_seven_segments(text: str):
    rows = ["", "", ""]
    for char, dot in display_cells(text):
        lit = SEGMENTS[char]
        rows[0] += " " + ("_" if "a" in lit else " ") + "  "
        rows[1] += ("|" if "f" in lit else " ") + ("_" if "g" in lit else " ") + ("|" if "b" in lit else " ") + " "
        rows[2] += ("|" if "e" in lit else " ") + ("_" if "d" in lit else " ") + ("|" if "c" in lit else " ")
        rows[2] += "." if dot else " "
    return rows


class Terminal:
    """Keeps the display drawing at a fixed place, log lines scroll above it."""

    def __init__(self, plain: bool, verbose: bool):
        self.plain = plain
        self.verbose = verbose
        self.drawn_lines = 0
        self.last_display = None
        if os.name == "nt" and not plain:
            os.system("")  # enables ANSI escape sequences in the Windows console

    def _clear_drawing(self):
        if self.drawn_lines:
            sys.stdout.write(f"\x1b[{self.drawn_lines}F\x1b[J")
            self.drawn_lines = 0

    def log(self, text: str):
        if not self.plain:
            self._clear_drawing()
        print(text)
        self.last_display = None

    def show(self, elapsed: float, display: str, status: str):
        if self.plain:
            if display != self.last_display or self.verbose:
                print(f"{elapsed:7.1f}s  [{display}]" + (f"  {status}" if self.verbose else ""))
                self.last_display = display
            return
        rows = draw_seven_segments(display)
        width = len(rows[0])
        lines = ["  +" + "-" * (width + 2) + "+"]
        lines += [f"  | {row} |" for row in rows]
        lines += ["  +" + "-" * (width + 2) + "+", f"  [{display}]  {elapsed:6.1f}s  {status}"]
        self._clear_drawing()
        sys.stdout.write("".join(line + "\x1b[K\n" for line in lines))
        sys.stdout.flush()
        self.drawn_lines = len(lines)


def load_eeprom(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def read_pads(board: Board):
    try:
        readings = board.channel_weights(WEIGHING_PAD_COUNT)
        values = [value for value, _ in readings]
        return None if None in values else values
    except (BoardError, ValueError, OSError):
        return None


def connect(board: Board, terminal: Terminal):
    while True:
        try:
            return board.discover()
        except (BoardError, OSError) as error:
            terminal.log(f"board not found yet: {error}")


def status_line(firmware: ScaleFirmware, raw) -> str:
    if raw is None or firmware.zero is None:
        return f"{firmware.state:9} no reading"
    return f"{firmware.state:9} {firmware.total_kg(raw):8.3f} kg  raw {raw}"


def run(board: Board, firmware: ScaleFirmware, eeprom: Path, terminal: Terminal):
    connect(board, terminal)
    start = time.monotonic()
    while True:
        now = time.monotonic()
        raw = read_pads(board)
        display = firmware.tick(raw, now)
        if firmware.eeprom_to_save:
            eeprom.write_text(json.dumps(firmware.eeprom_to_save))
            terminal.log(f"EEPROM saved to {eeprom}: {firmware.eeprom_to_save}")
            firmware.eeprom_to_save = None
        terminal.show(now - start, display, status_line(firmware, raw))
        if firmware.powered_off:
            terminal.log("Scale switched off (30 s at 0). Run the program again to wake it up.")
            return
        time.sleep(max(0.0, POLL_PERIOD_S - (time.monotonic() - now)))


def main():
    parser = argparse.ArgumentParser(description="PC simulation of the bathroom-scale firmware")
    parser.add_argument("port", help="serial port, e.g. COM7 or /dev/ttyUSB0")
    parser.add_argument("--eeprom", type=Path, default=Path("scale_eeprom.json"))
    parser.add_argument("--plain", action="store_true", help="one line per display change instead of a fixed drawing")
    parser.add_argument("--verbose", action="store_true", help="with --plain: print every tick with kg, raw and state")
    args = parser.parse_args()

    import serial  # pyserial

    eeprom = load_eeprom(args.eeprom)
    terminal = Terminal(args.plain, args.verbose)
    terminal.log(f"EEPROM: {eeprom if eeprom else 'empty, scale not calibrated'}")
    port = serial.Serial(args.port, 9600, bytesize=8, parity="N", stopbits=1, timeout=0.05)
    try:
        run(Board(port), ScaleFirmware(eeprom), args.eeprom, terminal)
    except KeyboardInterrupt:
        pass
    finally:
        port.close()


if __name__ == "__main__":
    main()
