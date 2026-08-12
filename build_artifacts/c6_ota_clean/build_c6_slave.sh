#!/usr/bin/env bash
set -euo pipefail

repo=/workspace/esp-hosted-mcu
commit=dd95bdf3316fc8c6110b387855033a26c0aa2447
test "$(git -C "${IDF_PATH}" describe --tags --always)" = v5.5.1

git config --global http.version HTTP/1.1
if [ ! -d "${repo}/.git" ]; then
    git clone https://github.com/CorruptName/esp-hosted-mcu.git "${repo}"
fi

cd "${repo}"
git fetch origin "${commit}"
git checkout "${commit}"
git submodule update --init --recursive
test "$(git rev-parse HEAD)" = "${commit}"

cd slave
rm -rf build sdkconfig sdkconfig.old
sdkconfig_defaults='sdkconfig.defaults;sdkconfig.defaults.esp32c6;sdkconfig.espnow'
idf.py -D "SDKCONFIG_DEFAULTS=${sdkconfig_defaults}" set-target esp32c6
idf.py -D "SDKCONFIG_DEFAULTS=${sdkconfig_defaults}" build

application=build/network_adapter.bin
elf=build/network_adapter.elf
test -f "${application}"
grep -q '^CONFIG_ESP_HOSTED_ENABLE_PEER_DATA_TRANSFER=y$' sdkconfig
grep -q '^CONFIG_ESP_HOSTED_ENABLE_ESPNOW=y$' sdkconfig
nm "${elf}" > /tmp/network_adapter_symbols.txt
grep -q 'esp_hosted_espnow_init' /tmp/network_adapter_symbols.txt
grep -q ' esp_now_send$' /tmp/network_adapter_symbols.txt
cp "${application}" /out/network_adapter-esp32c6.bin
sha256sum "${application}" | tee /out/network_adapter-esp32c6.sha256
stat -c '%s bytes' "${application}" | tee /out/network_adapter-esp32c6.size

echo C6_SLAVE_BUILD_OK