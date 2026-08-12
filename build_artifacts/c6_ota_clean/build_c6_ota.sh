#!/usr/bin/env bash
set -euo pipefail

retry() {
    local attempt
    for attempt in 1 2 3 4; do
        if "$@"; then
            return 0
        fi
        echo "Network operation failed (attempt ${attempt}/4): $*" >&2
    done
    return 1
}

test "${IDF_PATH}" = /opt/esp/idf
git config --global http.version HTTP/1.1
git clone --no-hardlinks /source /tmp/lvgl_micropython
cd /tmp/lvgl_micropython
retry git submodule update --init -- lib/lvgl lib/micropython lib/pycparser
retry git -C lib/micropython submodule update --init -- \
    lib/berkeley-db-1.xx \
    lib/mbedtls \
    lib/micropython-lib \
    lib/tinyusb

cp /source/ext_mod/micropython.cmake ext_mod/micropython.cmake
mkdir -p ext_mod/c6_ota examples/waveshare_esp32_p4_4_3 stubs
cp /source/ext_mod/c6_ota/c6_ota.c ext_mod/c6_ota/c6_ota.c
cp /source/ext_mod/c6_ota/micropython.cmake ext_mod/c6_ota/micropython.cmake
cp /source/examples/waveshare_esp32_p4_4_3/c6_ota_install.py examples/waveshare_esp32_p4_4_3/c6_ota_install.py
cp /source/stubs/c6_ota.pyi stubs/c6_ota.pyi
cp /source/display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3.toml \
    display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3.toml

make -C lib/micropython/mpy-cross clean
make -C lib/micropython/mpy-cross
export MICROPY_MPYCROSS="${PWD}/lib/micropython/mpy-cross/build/mpy-cross"

git -C "${IDF_PATH}" describe --tags --always
git -C "${IDF_PATH}" rev-parse HEAD
firmware=build/lvgl_micropy_ESP32_GENERIC_P4-C6_WIFI-32.bin
rm -f "${firmware}"
python3 make.py esp32 \
    BOARD=ESP32_GENERIC_P4 \
    BOARD_VARIANT=C6_WIFI \
    --flash-size=32 \
    --toml=display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3.toml

qstr=lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI/genhdr/qstrdefs.generated.h
elf=lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI/micropython.elf

test -f "${firmware}"
grep MP_QSTR_c6_ota "${qstr}" > /out/c6_ota_qstr.txt
test -f "${elf}"
flash_header=$(od -An -tx1 -j $((0x2003)) -N1 "${firmware}" | tr -d '[:space:]')
if [ "${flash_header}" != "50" ]; then
    echo "Unsafe bootloader flash header: expected 0x50 (40 MHz), got 0x${flash_header}" >&2
    exit 1
fi
dd if="${firmware}" of=/tmp/c6-ota-bootloader.bin bs=1 skip=$((0x2000)) count=$((0x6000)) status=none
python3 -c 'from esptool.bin_image import LoadFirmwareImage; image = LoadFirmwareImage("esp32p4", "/tmp/c6-ota-bootloader.bin"); assert (image.min_rev_full, image.max_rev_full) == (100, 199), (image.min_rev_full, image.max_rev_full); print("Bootloader revision range: v1.0 to v1.99")'
cp /tmp/c6-ota-bootloader.bin /out/bootloader-c6-ota.bin
if nm -u "${elf}" | grep -E 'esp_hosted_slave_ota_(begin|write|end|activate)'; then
    echo "Unresolved ESP-Hosted OTA symbols found" >&2
    exit 1
fi
nm "${elf}" | grep -E 'esp_hosted_slave_ota_(begin|write|end|activate)' > /out/c6_ota_symbols.txt

cp "${firmware}" /out/firmware-waveshare-esp32-p4-4.3-c6-ota.bin
sha256sum "${firmware}" | tee /out/firmware.sha256
stat -c '%s bytes' "${firmware}" | tee /out/firmware.size
echo C6_OTA_CLEAN_BUILD_OK