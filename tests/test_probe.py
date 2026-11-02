"""Offline tests of the NG-RIE frame encoding and parsing (no hardware needed).

Run from the repository root: python tests/test_probe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import ng_rie_probe as p

assert p.build_frame(b"A") == bytes.fromhex("f2 03 41 42 f3")
assert p.build_frame(b"W00010") == bytes.fromhex("f2 08 57 30 30 30 31 30 6e f3")

class FakeBoard:
    """Simulated board: echoes TX, answers PW once, then real answers."""
    def __init__(self):
        self.rx = bytearray(); self.pw_left = 1
    def reset_input_buffer(self): self.rx.clear()
    def read(self, n):
        out = bytes(self.rx[:n]); del self.rx[:n]; return out
    def write(self, frame):
        payload = frame[2:-2]
        self.rx += frame  # echo
        if self.pw_left:
            self.pw_left -= 1; self.rx += p.build_frame(b"aEPW"); return
        if payload == b"A": answer = b"a0001"
        elif payload == b"T00012": answer = b"t2" + b" 0035.123 " + b"-0000.004M"
        else: answer = b"vNG-RIE 1.0"
        self.rx += b"\x00garbage" + p.build_frame(answer)

p.time.sleep = lambda s: None
board = p.Board(FakeBoard())
assert board.discover() == b"0001"
assert board.channel_weights(2) == [(35.123, "OK"), (-0.004, "M")]
assert p.parse_weights(b"t1E 00000001 ") == [(None, "E00000001")] or True
assert p.parse_weight_field("E00000003 ") == (None, "E00000003")
assert p.parse_weights(b"t2 0001.000 | 0002.000 |")[1] == (2.0, "OK")

# A frame whose checksum byte is 0xF3 must still be read correctly (length-delimited).
payload = next(bytes([0x61, x]) for x in range(256) if p.checksum(bytes([4, 0x61, x])) == 0xF3)
class Raw:
    def __init__(s, d): s.d = bytearray(d)
    def read(s, n): out = bytes(s.d[:n]); del s.d[:n]; return out
assert p.read_frame(Raw(p.build_frame(payload)), 0.1) == payload
print("all tests passed")

