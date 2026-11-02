"""Offline scenario tests of the scale firmware state machine on a simulated board.

Run from the repository root: python tests/test_firmware.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import scale_firmware_sim as s

TRUE_GAINS = (0.5878, 3.738)   # g per count, measured on the real board
OFFSETS = (3554, -1091)
random.seed(1)

class World:
    def __init__(self, gains):
        self.fw = s.ScaleFirmware(gains, 1000.0)
        self.t = 0.0
        self.load = [0.0, 0.0]  # true grams on pad 0 (right) and pad 1 (left)
        self.trace = []
    def raw(self, jitter_g):
        return [round(o + (l + random.uniform(-jitter_g, jitter_g)) / k) for o, l, k in zip(OFFSETS, self.load, TRUE_GAINS)]
    def run(self, seconds, jitter_g=1.0, comm_ok=True):
        for _ in range(round(seconds / s.POLL_PERIOD_S)):
            self.t += s.POLL_PERIOD_S
            d = self.fw.tick(self.raw(jitter_g) if comm_ok else None, self.t)
            if not self.trace or self.trace[-1] != d:
                self.trace.append(d)
        return self.trace[-1]

def check_kg(label, got, expected_kg):
    assert abs(float(got) - expected_kg) <= 0.1 + 1e-9, f"{label}: got {got!r}, expected {expected_kg} +-0.1"
    print(f"  ok  {label:45} [{got}]")

def check(label, got, expected):
    assert got == expected, f"{label}: got {got!r}, expected {expected!r}"
    print(f"  ok  {label:45} [{got}]")

print("Calibration from scratch (default gains), triggered by stepping off:")
w = World([1.0, 1.0])
w.load = [45000, 35000]; w.run(1.4, jitter_g=300); check("boot tare done within 1.4 s while standing", w.fw.state, "WEIGH")
w.load = [0, 0];         check("step off -> CAL", w.run(1), "CAL ")
check("empty tare done -> PL L", w.run(4), "PL L")
w.load = [20, 980];      check("1 kg on the left cell -> PL r", w.run(3), "PL r")
w.load = [985, 15];      check("moved to the right cell -> donE", w.run(2.5), "donE")
check("then the mass reads 1.0", w.run(4), "  1.0")
print("  gains found:", [round(k, 4) for k in w.fw.gains], " true:", TRUE_GAINS)
w.load = [0, 0];         check("mass removed", w.run(2), "   0")
w.load = [52000, 28000]; check_kg("80 kg person, swaying +-80 g", w.run(6, jitter_g=80), 80.0)
w.load = [30000, 50000]; check_kg("same person leaning left (stays locked)", w.run(3, jitter_g=80), 80.0)
w.load = [56000, 56000]; check("112 kg person", w.run(6, jitter_g=80), " 112")
w.load = [0, 0];         check("step off", w.run(2), "   0")
saved = w.fw.gains

print("Normal power-on with saved gains:")
w = World(saved)
check("power on empty", w.run(2), "   0")
w.load = [33700, 33700]; check_kg("67.4 kg", w.run(6, jitter_g=80), 67.4)
before = len(w.trace); w.run(10, jitter_g=80)
check("locked: no change over 10 s of swaying", len(w.trace) - before, 0)
w.load = [70000, 10000]; check("one cell overloaded", w.run(1, jitter_g=80), "  OL")
w.load = [0, 0];         w.run(2)
check("comm lost 0.6 s keeps display", w.run(0.6, comm_ok=False), "   0")
check("comm lost 1 s -> ----", w.run(0.6, comm_ok=False), "----")
check("comm back", w.run(1), "   0")

print("Step-on ergonomics (sway +-300 g, much more than a calm person):")
w = World(saved)
w.run(2)
start = len(w.trace); t0 = w.t
w.load = [20000, 20000]; w.run(0.4, jitter_g=2000)
w.load = [38000, 38000]
times = []
for _ in range(40):
    before = len(w.trace); w.run(0.2, jitter_g=300)
    if len(w.trace) != before: times.append(round(w.t - t0, 1))
shown = w.trace[start:]
print("  displays after stepping on:", shown, "at t =", times)
values = [d for d in shown if d != s.BLANK]
check("at most 8 values before it settles", len(values) <= 8, True)
check("blinks twice when locked", shown[-5:].count(s.BLANK), 2)
check("settled before 5.5 s", times[-1] <= 5.5, True)
check_kg("settled value", shown[-1], 76.0)

print("Calibration abandoned:")
w = World(saved)
w.load = [40000, 40000]; w.run(3, jitter_g=80)
w.load = [0, 0];         w.run(5)
check("waiting for the mass", w.trace[-1], "PL L")
w.run(61)
check("timeout after 60 s: Err, re-tare, 0", w.trace[-3:], ["PL L", "Err ", "   0"])
w = World(saved)
w.load = [40000, 40000]; w.run(3, jitter_g=80)
w.load = [0, 0];         w.run(5)
w.load = [40000, 40000]; check("someone steps back on -> Err", w.run(0.4, jitter_g=80), "Err ")
k = s.solve_gains([105, 251], [1663, 6], 1000)
assert abs(k[0] - 0.5878) < 0.001 and abs(k[1] - 3.738) < 0.002, k
try:
    s.solve_gains([500, 500], [510, 490], 1000); raise SystemExit("expected rejection")
except ValueError:
    pass
assert [s.format_weight(x) for x in (0.1, -0.15, 67.44, 99.94, 99.96, 112.4, -1.26)] == ["0", "0", "67.4", "99.9", "100", "112", "-1.3"]
for text in ["0", "67.4", "-1.3", "112", "-99.9"]:
    s.render(text)
print("all firmware tests passed")
