# ESP32-P4 Firmware Builds

Use the checked-in build wrapper for Waveshare ESP32-P4 firmware. Do not run the
firmware build directly against a Windows-mounted source tree: Docker Desktop
file-system translation makes CMake and Ninja dramatically slower.

## Requirements

- Windows with WSL 2
- A Debian WSL distribution
- Docker Desktop with integration enabled for Debian

The wrapper installs `rsync` in Debian when it is missing. The pinned build
image is based on `espressif/idf:v5.5.1` and includes `toml==0.10.2`.

## Build

From PowerShell at the repository root:

```powershell
.\tools\build_waveshare.ps1
```

This is a local development build of only the Waveshare ESP-NOW variant. It
may reuse incremental caches and is intended for iteration and hardware tests;
it is not an installer release build.

The first run creates a persistent native Linux mirror at:

```text
$HOME/esp-idf/lvgl_micropython-build
```

Set `LVGL_MICROPYTHON_BUILD_ROOT` inside Debian to override that location.
Subsequent runs synchronize current source changes into the mirror while
retaining native build and component caches. On the validated workstation, a
no-change repeat build completes in about two minutes instead of rebuilding
through Docker Desktop's Windows file-system translation.

The validated ESP-Hosted fork is always checked out recursively at commit:

```text
dd95bdf3316fc8c6110b387855033a26c0aa2447
```

A successful build copies these files back to `build_artifacts/`:

```text
waveshare-esp32-p4-4.3-espnow.bin
waveshare-esp32-p4-4.3-espnow.bin.sha256
```

Use a clean native build only when needed:

```powershell
.\tools\build_waveshare.ps1 -Clean
```

## Installer Firmware Releases

Installer-compatible firmware is published only from committed source using
the `Build installer firmware` GitHub Actions workflow. It performs clean builds
of these four 32 MiB variants:

| Artifact ID | Filename |
| --- | --- |
| `dev-standard` | `esp32-p4.bin` |
| `dev-espnow` | `esp32-p4-espnow.bin` |
| `waveshare-standard` | `waveshare-esp32-p4-4.3.bin` |
| `waveshare-espnow` | `waveshare-esp32-p4-4.3-espnow.bin` |

All four builds reserve a fixed 5 MiB application partition at `0x10000`, so
the FAT VFS always begins at `0x510000`. Both Waveshare configurations use the
validated PPA-disabled profile, 16 ms LVGL task-handler period, 64-byte draw
buffer alignment, and frame-completion-safe DSI buffer ownership.

A manual workflow run produces a reviewable CI artifact. Pushing an immutable
`firmware-v*` tag additionally publishes the four uniquely named binaries,
individual checksums, `SHA256SUMS`, and `firmware-release.json` as GitHub
Release assets. The release index records the producer, MicroPython, LVGL,
ESP-IDF, and ESP-Hosted commits.

The installer imports an explicit producer release as one complete set. Local
development builds never update or publish installer firmware automatically.

### Release Acceptance Sequence

1. Push the candidate commit and run `Build installer firmware` manually.
2. Download that exact CI artifact and record its producer commit and four
	SHA-256 values.
3. Hardware-test all four images from that artifact:
	- Generic standard: erase/flash, boot, REPL, and VFS.
	- Generic ESP-NOW: standard checks plus Wi-Fi and ESP-NOW with matched C6.
	- Waveshare standard: display redraw quality, touch, audio, SD, RTC, and VFS.
	- Waveshare ESP-NOW: all Waveshare checks plus C6 identity and ESP-NOW.
4. After the candidate artifact passes, create `firmware-v*` on the same
	producer commit. Never move or recreate that tag.
5. In the installer repository, import the explicit tag:

	```bash
	python update_firmware.py --sync-release firmware-vX.Y.Z
	```

6. Test all four selections from the resulting installer ZIP, merge the
	reviewable importer PR, then create the installer `v*` tag from that exact
	validated merge commit.

The producer release contains the four binaries, their individual checksum
files, `SHA256SUMS`, and `firmware-release.json`. The installer import is
all-or-nothing and rejects mismatched ESP-Hosted or C6 identities.

## Flashing

The build wrapper never accesses serial ports and never flashes hardware.
Flashing remains a separate manual step so the board can be placed in download
mode and explicitly confirmed before upload.

## Updating The Toolchain

Change toolchain pins only in these files and validate both a clean and an
incremental build:

- `tools/docker/esp32-p4.Dockerfile`
- `tools/build_waveshare_debian.sh`

Do not substitute an unpinned ESP-IDF image or an upstream ESP-Hosted component
for release firmware.
