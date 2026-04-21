# Code Buddy

Code Buddy turns an M5Stack StickS3 into a Bluetooth approval device for Codex CLI on macOS. Flash the StickS3 once, install `code-buddy`, then keep using `codex` normally while approval prompts appear on the device.

This project is ported from Anthropic's [claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy), then adapted for Codex CLI, the StickS3 hardware path, and the `code-buddy` macOS setup flow.

> Building your own hardware client instead? See [firmware/REFERENCE.md](firmware/REFERENCE.md) for the BLE protocol and JSON payloads.

## What You Need

- A Mac
- An M5Stack StickS3
- Codex already installed on the Mac

## Device Setup

1. Download `code-buddy-sticks3-v{version}-full.bin` from GitHub Releases.
2. Flash that merged image onto the StickS3.

Primary path:

- If this release publishes a web flasher page, use it and write the merged image at `0x0`.

Fallback path:

```bash
esptool --chip esp32s3 --port /dev/cu.usbmodem101 --baud 460800 write_flash 0x0 code-buddy-sticks3-v0.1.1-full.bin
```

Developer release build:

```bash
./scripts/build-firmware-release.sh
```

## Mac Setup

Install:

```bash
brew install CharlexH/tap/code-buddy
```

First run:

```bash
code-buddy
```

That setup flow will:

- install the native Bluetooth helper
- pair with a `Codex-*` StickS3 and prompt if multiple devices are found
- sync device time
- install the launchd agent
- install the local `codex` shim
- add `~/.code-buddy/bin` to `~/.zprofile`

## Daily Use

After setup, open a new shell and use Codex normally:

```bash
codex
```

Code Buddy will intercept the CLI session, keep the StickS3 linked, and show approval prompts on the device.

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

The screen auto-powers off after 30 seconds of inactivity and stays on while an approval prompt is pending. Any button press wakes it.

## The Seven States

| State       | Trigger                     | Feel                        |
| ----------- | --------------------------- | --------------------------- |
| `sleep`     | bridge not connected        | eyes closed, slow breathing |
| `idle`      | connected, nothing urgent   | blinking, looking around    |
| `busy`      | sessions actively running   | sweating, working           |
| `attention` | approval pending            | alert, **LED blinks**       |
| `celebrate` | level up (every 50K tokens) | confetti, bouncing          |
| `dizzy`     | you shook the stick         | spiral eyes, wobbling       |
| `heart`     | approved in under 5s        | floating hearts             |

## ASCII Pets

The firmware ships with eighteen ASCII pets. Each one has seven animations: `sleep`, `idle`, `busy`, `attention`, `celebrate`, `dizzy`, and `heart`.

Use `menu -> next pet` on the device to cycle through them. The selection is saved to device storage, so your pet stays selected after reboot.

## GIF Pets

If you want a custom GIF character instead of an ASCII buddy, the firmware also supports character packs. A pack is a folder with a `manifest.json` plus 96px-wide GIFs for the same seven states.

```json
{
  "name": "bufo",
  "colors": {
    "body": "#6B8E23",
    "bg": "#000000",
    "text": "#FFFFFF",
    "textDim": "#808080",
    "ink": "#000000"
  },
  "states": {
    "sleep": "sleep.gif",
    "idle": ["idle_0.gif", "idle_1.gif", "idle_2.gif"],
    "busy": "busy.gif",
    "attention": "attention.gif",
    "celebrate": "celebrate.gif",
    "dizzy": "dizzy.gif",
    "heart": "heart.gif"
  }
}
```

Notes:

- `idle` can be a single GIF or an array of GIFs; arrays rotate at loop boundaries.
- Keep GIFs at 96px width. Heights up to about 140px fit well on the StickS3 screen.
- See [firmware/characters/bufo/](firmware/characters/bufo/) for a working example.
- For asset prep and USB flashing, see [firmware/tools/prep_character.py](firmware/tools/prep_character.py) and [firmware/tools/flash_character.py](firmware/tools/flash_character.py).

## Recovery

```bash
code-buddy doctor
code-buddy repair
code-buddy uninstall
```

`doctor` explains what is wrong, why it happened, and what to do next.

## From Source

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/code-buddy
```

## Verification

- Host tests: `.venv/bin/pytest -q`
- Firmware build: `cd firmware && pio run`
