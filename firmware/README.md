# Code Buddy Firmware

This firmware targets the M5Stack StickS3 and turns it into a Code Buddy approval device for Codex CLI.

> Building your own hardware client instead? See [REFERENCE.md](REFERENCE.md) for the BLE protocol and JSON payloads.

## User Flashing Path

1. Download `code-buddy-sticks3-v{version}-full.bin` from GitHub Releases.
2. Flash that merged image onto the StickS3 at address `0x0`.

Primary path:

- If this release publishes a web flasher page, use it.

Fallback path:

```bash
esptool --chip esp32s3 --port /dev/cu.usbmodem101 --baud 460800 write_flash 0x0 code-buddy-sticks3-v0.1.1-full.bin
```

After flashing, go back to the Mac and run:

```bash
code-buddy
```

That will request Bluetooth permission, pair the StickS3, sync time, and finish the Mac-side setup.

## Developer Build Path

Build and flash directly with PlatformIO:

```bash
pio run -t upload
```

If you need a clean reflash:

```bash
pio run -t erase && pio run -t upload
```

Build the merged GitHub Release artifact:

```bash
../scripts/build-firmware-release.sh
```

## Controls

|                         | Normal               | Pet         | Info        | Approval    |
| ----------------------- | -------------------- | ----------- | ----------- | ----------- |
| **A** (front)           | next screen          | next screen | next screen | **approve** |
| **B** (right)           | scroll transcript    | next page   | next page   | **deny**    |
| **Hold A**              | menu                 | menu        | menu        | menu        |
| **Power** (left, short) | toggle screen off    |             |             |             |
| **Power** (left, ~6s)   | hard power off       |             |             |             |
| **Shake**               | dizzy                |             |             | —           |
| **Face-down**           | nap (energy refills) |             |             |             |

The screen auto-powers off after 30 seconds of inactivity and stays on while an approval is pending.

## GIF Characters

If you want a custom GIF character instead of the ASCII buddy, push a character pack folder over the buddy transfer path. The bridge streams it over BLE and the stick switches to GIF mode live. `Settings -> delete char` returns to ASCII mode.

Character packs need a `manifest.json` plus 96px-wide GIFs. See `characters/bufo/` for a working example.

## Project Layout

```text
src/
  main.cpp       main loop, state machine, UI screens
  buddy.cpp      ASCII species render helpers
  buddies/       one file per species
  ble_bridge.cpp Nordic UART service
  character.cpp  GIF decode + render
  data.h         wire protocol and JSON parse
  xfer.h         folder push receiver
  stats.h        persisted settings and counters
characters/      example GIF character packs
tools/           asset and flashing helpers
```
