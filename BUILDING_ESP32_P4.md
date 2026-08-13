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
