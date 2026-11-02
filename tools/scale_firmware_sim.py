#!/usr/bin/env python3
"""PC simulation of the bathroom-scale firmware planned for the Arduino.

Same state machine as the future firmware, fed by the real NG-RIE board through
the USB/RS-485 cable. Each printed line is what the 4-digit display shows
(the decimal point does not use a digit).

    python scale_firmware_sim.py COM7 --mass 1000 [--verbose]

Needs ng_rie_probe.py in the same folder. Read-only for the board: the
calibration is kept in scale_eeprom.json, which stands for the Arduino EEPROM.

Usage:
- Power on empty: automatic tare, display 0. Step on: a 1 s average is shown twice
  per second, then the display locks on a 2 s average and blinks twice.
- Calibration: power on while standing on the scale, wait for 0, then step off. A stable
  weight below -40 kg starts it: CAL (empty tare), PL L (mass on the left
  load cell), PL r (mass moved to the right load cell), donE.
"""
import argparse
import json
import statistics
import time
from collections import deque
from pathlib import Path

from ng_rie_probe import Board, BoardError

POLL_PERIOD_S = 0.2
WEIGHING_PAD_COUNT = 2
STABLE_SAMPLES = 5
STABLE_SPREAD_KG = 0.2
# A person standing still sways too much for the weighing criterion; the boot
# tare must still succeed with someone on the scale (calibration gesture).
BOOT_STABLE_SPREAD_KG = 2.0
# Person weighing: wait for the step-on to settle, show a slow running average,
# then lock on the average of the last samples (sway averages out).
MIN_PERSON_KG = 2.0
SETTLE_S = 0.6
REFRESH_S = 0.5
SHORT_AVERAGE_SAMPLES = 5
LOCK_AVERAGE_SAMPLES = 10
LOCK_STDEV_KG = 0.15
MAX_MEASURE_S = 5.0
RELEASE_KG = 1.0
# Two short blinks tell the user the weight is final.
BLINK_COUNT = 2
BLINK_PHASE_S = 0.2
ZERO_BAND_KG = 0.2
OVERLOAD_PAD_KG = 60.0
CAL_TRIGGER_KG = -40.0
CAL_STABLE_SAMPLES = 8
CAL_STABLE_SPREAD_KG = 0.015
CAL_MIN_LOAD_RATIO = 0.2
CAL_MIN_POSITION_CHANGE = 0.3
CAL_ABORT_KG = 5.0
CAL_STEP_TIMEOUT_S = 60.0
MESSAGE_S = 2.0
COMM_LOSS_POLLS = 5
GAIN_RANGE = (0.01, 100.0)

NO_DATA = "----"
OVERLOAD = "  OL"
BLANK = "    "
SEVEN_SEGMENT_CHARS = set("0123456789 -AbCcdEFHhIJLnoOPrStUuy")


def solve_gains(delta_a, delta_b, mass_g: float):
    """Solve k0*a0 + k1*a1 = m and k0*b0 + k1*b1 = m (mass at two positions)."""
    det = delta_a[0] * delta_b[1] - delta_a[1] * delta_b[0]
    if abs(det) < 0.25 * (abs(delta_a[0] * delta_b[1]) + abs(delta_a[1] * delta_b[0])):
        raise ValueError("the two positions are too similar")
    k0 = mass_g * (delta_b[1] - delta_a[1]) / det
    k1 = mass_g * (delta_a[0] - delta_b[0]) / det
    return [k0, k1]


def format_weight(weight_kg: float) -> str:
    if abs(weight_kg) < ZERO_BAND_KG:
        return "0"
    rounded = round(weight_kg, 1)
    if -100.0 < rounded < 100.0:
        return f"{rounded:.1f}"
    return str(round(weight_kg))


def render(text: str) -> str:
    """Right-align on 4 digits; reject what a 7-segment display cannot show."""
    digits = text.replace(".", "")
    if len(digits) > 4 or not set(digits) <= SEVEN_SEGMENT_CHARS:
        raise ValueError(f"not displayable on 4 digits: {text!r}")
    return " " * (4 - len(digits)) + text


def load_share(pad_kg):
    total = sum(pad_kg)
    return pad_kg[0] / total if total else 0.5


class ScaleFirmware:
    """Display logic, one tick per board reading. To be ported as-is to the Arduino."""

    def __init__(self, gains, mass_g: float):
        self.gains = list(gains)
        self.mass_g = mass_g
        self.state = "BOOT"
        self.zero = None
        self.history = deque(maxlen=CAL_STABLE_SAMPLES)
        self.locked_kg = None
        self.measure_start = None
        self.locked_at = 0.0
        self.measure_totals = []
        self.next_refresh = 0.0
        self.message = None
        self.message_until = 0.0
        self.step_started = 0.0
        self.first_capture = None
        self.failures = 0
        self.display = NO_DATA
        self.new_gains_to_save = None

    def tick(self, raw, now: float) -> str:
        if raw is None:
            self.failures += 1
            if self.failures >= COMM_LOSS_POLLS:
                self.display = NO_DATA
            return self.display
        self.failures = 0
        self.history.append(list(raw))
        self.display = self._update(raw, now)
        return self.display

    def pad_kg(self, raw):
        return [k * (value - origin) / 1000 for k, value, origin in zip(self.gains, raw, self.zero)]

    def total_kg(self, raw) -> float:
        return sum(self.pad_kg(raw))

    def _stable_mean(self, samples: int, spread_kg: float):
        if len(self.history) < samples:
            return None
        recent = list(self.history)[-samples:]
        totals = [self.total_kg(sample) for sample in recent]
        if max(totals) - min(totals) > spread_kg:
            return None
        return [statistics.fmean(pad) for pad in zip(*recent)]

    def _show_message(self, text: str, now: float) -> str:
        self.message = text
        self.message_until = now + MESSAGE_S
        return text

    def _update(self, raw, now: float) -> str:
        if self.message and now < self.message_until:
            return self.message
        self.message = None
        if self.state == "BOOT":
            return self._boot(raw)
        if self.state == "WEIGH":
            return self._weigh(raw, now)
        return self._calibrate(raw, now)

    def _boot(self, raw) -> str:
        if self.zero is None:
            self.zero = list(raw)
        stable = self._stable_mean(STABLE_SAMPLES, BOOT_STABLE_SPREAD_KG)
        if stable is None:
            return NO_DATA
        self.zero = stable
        self._reset_measure()
        self.state = "WEIGH"
        return render("0")

    def _weigh(self, raw, now: float) -> str:
        if max(self.pad_kg(raw)) > OVERLOAD_PAD_KG:
            self._reset_measure()
            return OVERLOAD
        stable = self._stable_mean(STABLE_SAMPLES, STABLE_SPREAD_KG)
        if stable is not None and self.total_kg(stable) <= CAL_TRIGGER_KG:
            return self._start_calibration(now)
        recent = list(self.history)[-SHORT_AVERAGE_SAMPLES:]
        recent_kg = statistics.fmean(self.total_kg(sample) for sample in recent)
        if self.locked_kg is not None:
            if abs(recent_kg - self.locked_kg) <= RELEASE_KG:
                return self._locked_display(now)
            self._reset_measure()
        if recent_kg < MIN_PERSON_KG:
            # Empty scale or light object: nothing sways, show it directly.
            self._reset_measure()
            return render(format_weight(self.total_kg(raw)))
        return self._measure(raw, now)

    def _measure(self, raw, now: float) -> str:
        if self.measure_start is None:
            self.measure_start = now
            self.measure_totals = []
            self.next_refresh = now + SETTLE_S
        if now - self.measure_start < SETTLE_S:
            return self.display
        self.measure_totals.append(self.total_kg(raw))
        window = self.measure_totals[-LOCK_AVERAGE_SAMPLES:]
        full = len(window) == LOCK_AVERAGE_SAMPLES
        if full and (statistics.pstdev(window) <= LOCK_STDEV_KG or now - self.measure_start >= MAX_MEASURE_S):
            self.locked_kg = statistics.fmean(window)
            self.locked_at = now
            return self._locked_display(now)
        if now >= self.next_refresh:
            self.next_refresh = now + REFRESH_S
            return render(format_weight(statistics.fmean(window[-SHORT_AVERAGE_SAMPLES:])))
        return self.display

    def _locked_display(self, now: float) -> str:
        elapsed = now - self.locked_at
        blinking = elapsed < BLINK_COUNT * 2 * BLINK_PHASE_S
        if blinking and int(elapsed / BLINK_PHASE_S + 1e-6) % 2 == 0:
            return BLANK
        return render(format_weight(self.locked_kg))

    def _reset_measure(self):
        self.locked_kg = None
        self.measure_start = None

    def _start_calibration(self, now: float) -> str:
        self._reset_measure()
        self.state = "CAL_TARE"
        self.step_started = now
        return self._show_message("CAL ", now)

    def _next_step(self, state: str, now: float) -> str:
        self.state = state
        self.step_started = now
        return "PL L" if state == "CAL_LEFT" else "PL r"

    def _calibrate(self, raw, now: float) -> str:
        if now - self.step_started > CAL_STEP_TIMEOUT_S:
            return self._abort(now)
        stable = self._stable_mean(CAL_STABLE_SAMPLES, CAL_STABLE_SPREAD_KG)
        if self.state == "CAL_TARE":
            if stable is None:
                return "CAL "
            self.zero = stable
            return self._next_step("CAL_LEFT", now)
        prompt = "PL L" if self.state == "CAL_LEFT" else "PL r"
        if self.total_kg(raw) > CAL_ABORT_KG:
            return self._abort(now)
        if stable is None:
            return prompt
        load = self.pad_kg(stable)
        if sum(load) < CAL_MIN_LOAD_RATIO * self.mass_g / 1000:
            return prompt
        delta = [value - origin for value, origin in zip(stable, self.zero)]
        if self.state == "CAL_LEFT":
            self.first_capture = (delta, load_share(load))
            return self._next_step("CAL_RIGHT", now)
        if abs(load_share(load) - self.first_capture[1]) < CAL_MIN_POSITION_CHANGE:
            return prompt
        return self._finish(self.first_capture[0], delta, now)

    def _finish(self, delta_a, delta_b, now: float) -> str:
        try:
            gains = solve_gains(delta_a, delta_b, self.mass_g)
        except ValueError:
            return self._abort(now)
        if not all(GAIN_RANGE[0] < k < GAIN_RANGE[1] for k in gains):
            return self._abort(now)
        self.gains = gains
        self.new_gains_to_save = gains
        self._reset_measure()
        self.state = "WEIGH"
        return self._show_message("donE", now)

    def _abort(self, now: float) -> str:
        # Back to an automatic tare on the current load: nothing is saved.
        self.state = "BOOT"
        self.zero = None
        self.history.clear()
        return self._show_message("Err ", now)


def load_gains(path: Path):
    if path.exists():
        return json.loads(path.read_text())["gains"]
    return [1.0] * WEIGHING_PAD_COUNT


def read_pads(board: Board):
    try:
        readings = board.channel_weights(WEIGHING_PAD_COUNT)
        values = [value for value, _ in readings]
        return None if None in values else values
    except (BoardError, ValueError, OSError):
        return None


def connect(board: Board):
    while True:
        try:
            return board.discover()
        except (BoardError, OSError) as error:
            print(f"[{NO_DATA}]  ({error})")


def run(board: Board, firmware: ScaleFirmware, eeprom: Path, verbose: bool):
    connect(board)
    start = time.monotonic()
    shown = None
    while True:
        now = time.monotonic()
        raw = read_pads(board)
        display = firmware.tick(raw, now)
        if firmware.new_gains_to_save:
            eeprom.write_text(json.dumps({"gains": firmware.new_gains_to_save}))
            print(f"          (gains saved to {eeprom}: {firmware.new_gains_to_save})")
            firmware.new_gains_to_save = None
        if display != shown or verbose:
            details = ""
            if verbose and raw is not None and firmware.zero is not None:
                details = f"   {firmware.total_kg(raw):8.3f} kg  raw {raw}  {firmware.state}"
            print(f"{now - start:7.1f}s  [{display}]{details}")
            shown = display
        time.sleep(max(0.0, POLL_PERIOD_S - (time.monotonic() - now)))


def main():
    parser = argparse.ArgumentParser(description="PC simulation of the bathroom-scale firmware")
    parser.add_argument("port", help="serial port, e.g. COM7 or /dev/ttyUSB0")
    parser.add_argument("--mass", type=float, default=1000.0, help="calibration mass in grams")
    parser.add_argument("--eeprom", type=Path, default=Path("scale_eeprom.json"))
    parser.add_argument("--verbose", action="store_true", help="print every tick with kg and state")
    args = parser.parse_args()

    import serial  # pyserial

    gains = load_gains(args.eeprom)
    print(f"Gains: {gains} ({'from ' + str(args.eeprom) if args.eeprom.exists() else 'default, not calibrated'})")
    port = serial.Serial(args.port, 9600, bytesize=8, parity="N", stopbits=1, timeout=0.05)
    try:
        run(Board(port), ScaleFirmware(gains, args.mass), args.eeprom, args.verbose)
    except KeyboardInterrupt:
        pass
    finally:
        port.close()


if __name__ == "__main__":
    main()
