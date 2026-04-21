# Code Buddy

Code Buddy turns an M5Stack StickS3 into a Bluetooth approval device for Codex CLI on macOS. Flash the StickS3 once, install `code-buddy`, then keep using `codex` normally while approval prompts appear on the device.

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
esptool --chip esp32s3 --port /dev/cu.usbmodem101 --baud 460800 write_flash 0x0 code-buddy-sticks3-v0.1.0-full.bin
```

Developer release build:

```bash
./scripts/build-firmware-release.sh
```

## Mac Setup

Install:

```bash
brew install charlex/tap/code-buddy
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
