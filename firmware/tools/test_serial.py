#!/usr/bin/env python3
"""Prove the Stick reacts to serial JSON. Cycles connected states every 3s."""
import json, time, serial, glob, sys

ports = sorted(glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/cu.usbserial-*'))
if not ports: sys.exit("no stick found")
s = serial.Serial(ports[0], 115200)
print(f"writing to {ports[0]} — watch the Stick\n")
print("sleep requires the bridge to stop sending data for ~30s, so it is not exercised here\n")

states = [
    {"total": 0, "running": 0, "waiting": 0},  # → idle
    {"total": 1, "running": 1, "waiting": 0},  # → busy
    {"total": 2, "running": 1, "waiting": 1},  # → attention, LED blinks
]
for i in range(20):
    st = states[i % len(states)]
    s.write((json.dumps(st) + "\n").encode())
    print(f"  → {st}")
    time.sleep(3)
