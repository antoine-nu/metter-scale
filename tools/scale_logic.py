"""Bathroom-scale firmware logic, free of any I/O.

One tick per board reading (every POLL_PERIOD_S). The Arduino firmware will be a
port of ScaleFirmware; tools/scale_firmware_sim.py runs it on a PC against the
real board. Behaviour reference: docs/display-behaviour.md.
"""
import statistics
from collections import deque

POLL_PERIOD_S = 0.2
RIGHT_PAD = 0
LEFT_PAD = 1

BOOT_STABLE_SPREAD_KG = 2.0     # a person standing still must pass
BOOT_RETARE_LIMIT_KG = 2.0      # closer than this to the saved zero: fresh tare

STABLE_SAMPLES = 5
ZERO_BAND_KG = 0.2
MIN_PERSON_KG = 2.0
SETTLE_S = 0.6
REFRESH_S = 0.5
SHORT_AVERAGE_SAMPLES = 5
LOCK_AVERAGE_SAMPLES = 18
LOCK_STDEV_KG = 0.15
MAX_MEASURE_S = 6.5
RELEASE_KG = 1.0
BLINK_COUNT = 2
BLINK_PHASE_S = 0.2
OVERLOAD_PAD_KG = 60.0

# Zero tracking absorbs the slow drift of the load cells while the scale is empty.
ZERO_TRACK_KG = 0.3
ZERO_TRACK_SPREAD_KG = 0.03
AUTO_OFF_S = 30.0

# Hand presses on the left or right load cell act as buttons.
PRESS_MIN_KG = 0.5
PRESS_RELEASE_KG = 0.3
PRESS_MAX_KG = 30.0
PRESS_SIDE_SHARE = 0.7
HOLD_START_S = 0.6
CAL_TRIGGER_PRESSES = 3
CAL_TRIGGER_WINDOW_S = 4.0

CAL_STABLE_SAMPLES = 8
CAL_STABLE_SPREAD_KG = 0.015
DEFAULT_CAL_MASS_G = 1000
MASS_STEP_G = 5
MASS_FAST_STEP_G = 50
MASS_FAST_AFTER_S = 2.5
MASS_RANGE_G = (100, 9995)
MASS_ACCEPT_IDLE_S = 4.0
CAL_MIN_LOAD_RATIO = 0.2
CAL_MIN_POSITION_CHANGE = 0.3
CAL_ABORT_KG = 5.0
CAL_STEP_TIMEOUT_S = 60.0
GAIN_RANGE = (0.01, 100.0)

MESSAGE_S = 2.0
COMM_LOSS_POLLS = 5

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


def right_share(pad_kg) -> float:
    total = sum(pad_kg)
    return pad_kg[RIGHT_PAD] / total if total else 0.5


class PressDetector:
    """Turns hand presses on one load cell into button events."""

    def __init__(self):
        self.side = None        # "L", "R", "X" (too heavy: a person, ignored) or None
        self.started = 0.0

    def update(self, pad_kg, now: float):
        """Return "L" or "R" when a short press is released, else None."""
        total = sum(pad_kg)
        if total < PRESS_RELEASE_KG:
            short_press = self.side in ("L", "R") and now - self.started < HOLD_START_S
            event = self.side if short_press else None
            self.side = None
            return event
        if total > PRESS_MAX_KG:
            self.side = "X"
        elif self.side is None and total >= PRESS_MIN_KG:
            share = right_share(pad_kg)
            if share >= PRESS_SIDE_SHARE:
                self.side, self.started = "R", now
            elif share <= 1 - PRESS_SIDE_SHARE:
                self.side, self.started = "L", now
        return None

    def held_for(self, now: float) -> float:
        return now - self.started if self.side in ("L", "R") else 0.0


class ScaleFirmware:
    """Display logic, one tick per board reading. To be ported as-is to the Arduino."""

    def __init__(self, eeprom: dict):
        self.gains = list(eeprom.get("gains", [1.0, 1.0]))
        self.saved_zero = eeprom.get("zero")
        self.cal_mass_g = eeprom.get("cal_mass_g", DEFAULT_CAL_MASS_G)
        self.state = "BOOT"
        self.zero = None
        self.history = deque(maxlen=CAL_STABLE_SAMPLES)
        self.presses = PressDetector()
        self.left_presses = deque(maxlen=CAL_TRIGGER_PRESSES)
        self.locked_kg = None
        self.locked_at = 0.0
        self.measure_start = None
        self.measure_totals = []
        self.next_refresh = 0.0
        self.idle_since = None
        self.message = None
        self.message_start = 0.0
        self.message_until = 0.0
        self.message_blinks = False
        self.step_started = 0.0
        self.mass_activity = 0.0
        self.first_capture = None
        self.failures = 0
        self.display = NO_DATA
        self.eeprom_to_save = None
        self.powered_off = False

    def eeprom(self) -> dict:
        return {"gains": self.gains, "zero": self.zero, "cal_mass_g": self.cal_mass_g}

    def tick(self, raw, now: float) -> str:
        if self.powered_off:
            return BLANK
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

    def _recent(self, samples: int):
        return list(self.history)[-samples:]

    def _stable_mean(self, samples: int, spread_kg: float):
        if len(self.history) < samples:
            return None
        recent = self._recent(samples)
        totals = [self.total_kg(sample) for sample in recent]
        if max(totals) - min(totals) > spread_kg:
            return None
        return [statistics.fmean(pad) for pad in zip(*recent)]

    def _show_message(self, text: str, now: float, blinks: bool = False, duration: float = MESSAGE_S) -> str:
        self.message = text
        self.message_start = now
        self.message_until = now + duration
        self.message_blinks = blinks
        return self._message_display(now)

    def _message_display(self, now: float) -> str:
        blank_phase = int((now - self.message_start) / BLINK_PHASE_S + 1e-6) % 2 == 0
        return BLANK if self.message_blinks and blank_phase else self.message

    def _update(self, raw, now: float) -> str:
        if self.message and now < self.message_until - 1e-6:
            return self._message_display(now)
        self.message = None
        if self.state == "BOOT":
            return self._boot(raw, now)
        if self.state == "WEIGH":
            return self._weigh(raw, now)
        if self.state == "CAL_MASS":
            return self._set_mass(raw, now)
        return self._calibrate(raw, now)

    # --- Boot and weighing -------------------------------------------------

    def _boot(self, raw, now: float) -> str:
        if self.zero is None:
            self.zero = list(self.saved_zero or raw)
        stable = self._stable_mean(STABLE_SAMPLES, BOOT_STABLE_SPREAD_KG)
        if stable is None:
            return NO_DATA
        # With a saved zero, someone already standing on the scale is weighed at once.
        if self.saved_zero is None or abs(self.total_kg(stable)) < BOOT_RETARE_LIMIT_KG:
            self.zero = stable
        self._enter_weighing()
        return self._weigh(raw, now)

    def _enter_weighing(self):
        self._reset_measure()
        self.presses = PressDetector()
        self.left_presses.clear()
        self.idle_since = None
        self.state = "WEIGH"

    def _weigh(self, raw, now: float) -> str:
        pad_kg = self.pad_kg(raw)
        if max(pad_kg) > OVERLOAD_PAD_KG:
            self._reset_measure()
            return OVERLOAD
        if self.presses.update(pad_kg, now) == "L":
            self.left_presses.append(now)
            if len(self.left_presses) == CAL_TRIGGER_PRESSES and now - self.left_presses[0] <= CAL_TRIGGER_WINDOW_S:
                return self._start_calibration(now)
        recent_kg = statistics.fmean(self.total_kg(sample) for sample in self._recent(SHORT_AVERAGE_SAMPLES))
        if self._auto_off_due(recent_kg, now):
            return self._power_off()
        if self.locked_kg is not None:
            if abs(recent_kg - self.locked_kg) <= RELEASE_KG:
                return self._locked_display(now)
            self._reset_measure()
        if recent_kg < MIN_PERSON_KG:
            # Empty scale or light object: nothing sways, show it directly.
            self._reset_measure()
            self._track_zero()
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
        blinking = elapsed < BLINK_COUNT * 2 * BLINK_PHASE_S - 1e-6
        if blinking and int(elapsed / BLINK_PHASE_S + 1e-6) % 2 == 0:
            return BLANK
        return render(format_weight(self.locked_kg))

    def _reset_measure(self):
        self.locked_kg = None
        self.measure_start = None

    def _track_zero(self):
        if self.presses.side is not None or len(self.history) < STABLE_SAMPLES:
            return
        recent = self._recent(STABLE_SAMPLES)
        totals = [self.total_kg(sample) for sample in recent]
        if max(abs(t) for t in totals) < ZERO_TRACK_KG and max(totals) - min(totals) <= ZERO_TRACK_SPREAD_KG:
            self.zero = [statistics.fmean(pad) for pad in zip(*recent)]

    def _auto_off_due(self, recent_kg: float, now: float) -> bool:
        if abs(recent_kg) >= ZERO_BAND_KG or self.presses.side is not None:
            self.idle_since = None
            return False
        if self.idle_since is None:
            self.idle_since = now
        return now - self.idle_since >= AUTO_OFF_S

    def _power_off(self) -> str:
        self.powered_off = True
        self.eeprom_to_save = self.eeprom()
        return BLANK

    # --- Calibration -------------------------------------------------------

    def _start_calibration(self, now: float) -> str:
        self._reset_measure()
        self.state = "CAL_TARE"
        self.step_started = now
        return self._show_message("CAL ", now)

    def _mass_text(self) -> str:
        return render(str(self.cal_mass_g))

    def _set_mass(self, raw, now: float) -> str:
        released = self.presses.update(self.pad_kg(raw), now)
        held = self.presses.held_for(now)
        if released or self.presses.side is not None:
            self.mass_activity = now
        if released:
            self._change_mass(MASS_STEP_G if released == "R" else -MASS_STEP_G)
        elif held >= HOLD_START_S:
            step = MASS_FAST_STEP_G if held >= MASS_FAST_AFTER_S else MASS_STEP_G
            self._change_mass(step if self.presses.side == "R" else -step)
        elif now - self.mass_activity >= MASS_ACCEPT_IDLE_S:
            self.state = "CAL_LEFT"
            self.step_started = now + BLINK_COUNT * 2 * BLINK_PHASE_S
            return self._show_message(self._mass_text(), now, blinks=True, duration=BLINK_COUNT * 2 * BLINK_PHASE_S)
        return self._mass_text()

    def _change_mass(self, step_g: int):
        self.cal_mass_g = min(MASS_RANGE_G[1], max(MASS_RANGE_G[0], self.cal_mass_g + step_g))

    def _calibrate(self, raw, now: float) -> str:
        if now - self.step_started > CAL_STEP_TIMEOUT_S:
            return self._abort(now)
        stable = self._stable_mean(CAL_STABLE_SAMPLES, CAL_STABLE_SPREAD_KG)
        if self.state == "CAL_TARE":
            if stable is None:
                return "CAL "
            self.zero = stable
            self.presses = PressDetector()
            self.mass_activity = now
            self.state = "CAL_MASS"
            return self._mass_text()
        prompt = "PL L" if self.state == "CAL_LEFT" else "PL r"
        if self.total_kg(raw) > CAL_ABORT_KG:
            return self._abort(now)
        if stable is None:
            return prompt
        load = self.pad_kg(stable)
        if sum(load) < CAL_MIN_LOAD_RATIO * self.cal_mass_g / 1000:
            return prompt
        delta = [value - origin for value, origin in zip(stable, self.zero)]
        if self.state == "CAL_LEFT":
            self.first_capture = (delta, right_share(load))
            self.state = "CAL_RIGHT"
            self.step_started = now
            return "PL r"
        if abs(right_share(load) - self.first_capture[1]) < CAL_MIN_POSITION_CHANGE:
            return prompt
        return self._finish(self.first_capture[0], delta, now)

    def _finish(self, delta_a, delta_b, now: float) -> str:
        try:
            gains = solve_gains(delta_a, delta_b, self.cal_mass_g)
        except ValueError:
            return self._abort(now)
        if not all(GAIN_RANGE[0] < k < GAIN_RANGE[1] for k in gains):
            return self._abort(now)
        self.gains = gains
        self.eeprom_to_save = self.eeprom()
        self._enter_weighing()
        return self._show_message("donE", now)

    def _abort(self, now: float) -> str:
        # Back to an automatic tare on the current load: nothing is saved.
        self.state = "BOOT"
        self.zero = None
        self.history.clear()
        return self._show_message("Err ", now)
