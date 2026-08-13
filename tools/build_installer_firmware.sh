#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-build_artifacts/installer}"
HOSTED_REPOSITORY="https://github.com/CorruptName/esp-hosted-mcu.git"
HOSTED_COMMIT="dd95bdf3316fc8c6110b387855033a26c0aa2447"
HOSTED_PATH="lib/micropython/ports/esp32/components/espressif__esp_hosted"

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.bin "$OUTPUT_DIR"/*.sha256 "$OUTPUT_DIR"/firmware-release.json

if [[ ! -d "$HOSTED_PATH/.git" ]]; then
    rm -rf "$HOSTED_PATH"
    mkdir -p "$(dirname "$HOSTED_PATH")"
    git clone --recurse-submodules "$HOSTED_REPOSITORY" "$HOSTED_PATH"
fi
git -C "$HOSTED_PATH" fetch origin "$HOSTED_COMMIT"
git -C "$HOSTED_PATH" checkout --detach "$HOSTED_COMMIT"
git -C "$HOSTED_PATH" submodule update --init --recursive

clean_build() {
    rm -rf build lib/micropython/ports/esp32/build-ESP32_GENERIC_P4 \
        lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI
}

copy_artifact() {
    local source="$1"
    local name="$2"
    test -f "$source"
    cp "$source" "$OUTPUT_DIR/$name"
    (cd "$OUTPUT_DIR" && sha256sum "$name") | tee "$OUTPUT_DIR/$name.sha256"
}

clean_build
python3 make.py esp32 BOARD=ESP32_GENERIC_P4 --flash-size=32 \
    --partition-size=5242880 DISPLAY=all INDEV=all EXPANDER=all
copy_artifact build/lvgl_micropy_ESP32_GENERIC_P4-32.bin esp32-p4.bin

clean_build
python3 make.py esp32 BOARD=ESP32_GENERIC_P4 BOARD_VARIANT=C6_WIFI \
    --flash-size=32 --partition-size=5242880 \
    --enable-cdc-repl=y --enable-jtag-repl=n --enable-uart-repl=y
copy_artifact build/lvgl_micropy_ESP32_GENERIC_P4-C6_WIFI-32.bin esp32-p4-espnow.bin

clean_build
python3 make.py \
    --toml=display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3-Standard.toml
copy_artifact build/lvgl_micropy_ESP32_GENERIC_P4-32.bin waveshare-esp32-p4-4.3.bin

clean_build
python3 make.py \
    --toml=display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3.toml
copy_artifact build/lvgl_micropy_ESP32_GENERIC_P4-C6_WIFI-32.bin \
    waveshare-esp32-p4-4.3-espnow.bin

python3 tools/create_firmware_release.py --output "$OUTPUT_DIR"
