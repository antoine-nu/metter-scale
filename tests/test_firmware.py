"""Offline scenario tests of the scale firmware logic on a simulated board.

Run from the repository root: python tests/test_firmware.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import scale_logic as s  # noqa: E402
import scale_firmware_sim as sim  # noqa: E402

TRUE_GAINS = (0.5878, 3.738)   # g per count, measured on the real board
random.seed(1)


class World:
    """A simulated board. load = true grams on [pad 0 (right), pad 1 (left)]."""

    def __init__(self, eeprom=None):
        self.fw = s.ScaleFirmware(eeprom or {})
        self.t = 0.0
        self.offsets = [3554, -1091]
        self.load = [0.0, 0.0]
        self.trace = []

    def raw(self, jitter_g):
        return [round(o + (load + random.uniform(-jitter_g, jitter_g)) / k)
                for o, load, k in zip(self.offsets, self.load, TRUE_GAINS)]

    def run(self, seconds, jitter_g=1.0, comm_ok=True):
        for _ in range(round(seconds / s.POLL_PERIOD_S)):
            self.t += s.POLL_PERIOD_S
            display = self.fw.tick(self.raw(jitter_g) if comm_ok else None, self.t)
            if not self.trace or self.trace[-1] != display:
                self.trace.append(display)
        return self.trace[-1]

    def press(self, side, seconds=0.4):
        self.load = [5000, 0] if side == "R" else [0, 5000]
        self.run(seconds)
        self.load = [0, 0]
        return self.run(0.4)


def check(label, got, expected):
    assert got == expected, f"{label}: got {got!r}, expected {expected!r}"
    print(f"  ok  {label:55} [{got}]")


def check_kg(label, got, expected_kg):
    assert abs(float(got) - expected_kg) <= 0.1 + 1e-9, f"{label}: got {got!r}, expected {expected_kg} +-0.1"
    print(f"  ok  {label:55} [{got}]")


def calibrated_world():
    w = World()
    w.run(2)
    for _ in range(3):
        w.press("L")
    w.run(3)
    w.run(5)
    w.load = [20, 980]
    w.run(3)
    w.load = [985, 15]
    w.run(5)
    w.load = [0, 0]
    w.run(2)
    return w


print("Calibration triggered by 3 presses on the left load cell:")
w = World()
check("first power on, empty", w.run(2), "   0")
w.press("L")
w.press("L")
check("third short press on the left -> CAL", w.press("L"), "CAL ")
check("empty tare, then last calibration mass in g", w.run(3), "1000")
check("short press on the right: +5 g", w.press("R"), "1005")
check("short press on the left: -5 g", w.press("L"), "1000")
w.run(5)
check("4 s without press: mass blinks twice", w.trace[-5:], ["    ", "1000", "    ", "1000", "PL L"])
w.load = [20, 980]
check("mass on the left cell -> PL r", w.run(3), "PL r")
w.load = [985, 15]
check("moved to the right cell -> donE", w.run(2.5), "donE")
check("then the mass reads 1.0", w.run(3), "  1.0")
saved = w.fw.eeprom()
print("  gains found:", [round(k, 4) for k in saved["gains"]], " true:", TRUE_GAINS)
check("EEPROM: calibration mass kept", saved["cal_mass_g"], 1000)

print("Setting the calibration mass by holding a press:")
w = World()
w.run(2)
for _ in range(3):
    w.press("L")
w.run(3)
w.load = [5000, 0]
w.run(4)
up = w.fw.cal_mass_g
check("hold right 4 s: slow then fast increase", 1300 <= up <= 1500, True)
w.load = [0, 0]
w.run(0.4)
check("release after a hold adds no extra step", w.fw.cal_mass_g, up)
w.load = [0, 5000]
w.run(40)
check("hold left long enough: clamped at 100 g", w.trace[-1], " 100")

print("Weighing with a calibrated scale:")
w = calibrated_world()
eeprom = w.fw.eeprom()
w = World(eeprom)
check("power on empty", w.run(2), "   0")
w.load = [52000, 28000]
check_kg("80 kg person, swaying +-80 g", w.run(8, jitter_g=80), 80.0)
before = len(w.trace)
w.load = [30000, 50000]
w.run(10, jitter_g=80)
check("leaning left: locked value does not change", len(w.trace) - before, 0)
w.load = [56000, 56000]
check("112 kg person", w.run(8, jitter_g=80), " 112")
w.load = [70000, 10000]
check("one load cell overloaded", w.run(1, jitter_g=80), "  OL")
w.load = [0, 0]
check("step off", w.run(2), "   0")
check("comm lost 0.6 s keeps display", w.run(0.6, comm_ok=False), "   0")
check("comm lost 1 s -> ----", w.run(0.6, comm_ok=False), "----")
check("comm back", w.run(1), "   0")

print("Step-on ergonomics (sway +-300 g, much more than a calm person):")
w = World(eeprom)
w.run(2)
start, t0 = len(w.trace), w.t
w.load = [20000, 20000]
w.run(0.4, jitter_g=2000)
w.load = [38000, 38000]
times = []
for _ in range(50):
    before = len(w.trace)
    w.run(0.2, jitter_g=300)
    if len(w.trace) != before:
        times.append(round(w.t - t0, 1))
shown = w.trace[start:]
print("  displays after stepping on:", shown, "at t =", times)
check("blinks twice when locked", shown[-5:].count(s.BLANK), 2)
check("locked before 7 s", times[-1] <= 7.0, True)
check_kg("locked value", shown[-1], 76.0)

print("Step-on scale behaviour:")
w = World(eeprom)
w.load = [40000, 40000]
check_kg("already standing at power on: weighed at once", w.run(6, jitter_g=80), 80.0)
w = World(eeprom)
w.run(2)
w.load = [0, 20000]
w.run(0.2)
w.load = [40000, 40000]
w.run(5, jitter_g=80)
w.load = [0, 20000]
w.run(0.2)
w.load = [0, 0]
w.run(1)
check("stepping on and off left foot first: no calibration", w.fw.state, "WEIGH")

print("Zero tracking and auto power-off:")
w = World(eeprom)
w.run(2)
w.offsets = [3554 + 150, -1091 + 30]   # about 200 g of drift, scale empty
w.run(3)
w.load = [40000, 40000]
check_kg("drift absorbed while empty, person weighed right", w.run(8, jitter_g=80), 80.0)
w.load = [0, 0]
w.run(29)
check("still on after 29 s at 0", w.fw.powered_off, False)
w.run(2)
check("switched off after 30 s at 0", w.fw.powered_off, True)
check("zero saved to EEPROM at power off", w.fw.eeprom_to_save["zero"] is not None, True)

print("Calibration abandoned:")
w = World(eeprom)
w.run(2)
for _ in range(3):
    w.press("L")
w.run(3)
w.run(4.5)
check("waiting for the mass", w.trace[-1], "PL L")
w.run(64)
check("timeout after 60 s: Err, then re-tare", w.trace[-2:], ["Err ", "   0"])
w = World(eeprom)
w.run(2)
for _ in range(3):
    w.press("L")
w.run(7.5)
w.load = [40000, 40000]
check("someone steps on during PL L -> Err", w.run(0.4, jitter_g=80), "Err ")

print("Helpers:")
k = s.solve_gains([105, 251], [1663, 6], 1000)
assert abs(k[0] - 0.5878) < 0.001 and abs(k[1] - 3.738) < 0.002, k
try:
    s.solve_gains([500, 500], [510, 490], 1000)
    raise SystemExit("expected rejection")
except ValueError:
    pass
check("format_weight", [s.format_weight(x) for x in (0.1, -0.15, 67.44, 99.94, 99.96, 112.4, -1.26)],
      ["0", "0", "67.4", "99.9", "100", "112", "-1.3"])
check("every displayable char has a drawing", s.SEVEN_SEGMENT_CHARS <= set(sim.SEGMENTS), True)
print("  drawing of ' 67.4':")
for row in sim.draw_seven_segments(" 67.4"):
    print("     " + row)
print("all firmware tests passed")
