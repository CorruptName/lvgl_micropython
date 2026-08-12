# C6 OTA Pause Point

Status recorded on 2026-08-12.

## Verified Working Pair

- P4 firmware: `firmware-waveshare-esp32-p4-4.3-espnow-sdcard.bin`
- P4 SHA-256: `DE15BA706122AD50403EAD62A817AB4303A277E6BA94C7F5B3C8B0E3727DBFF3`
- P4 size: 3,511,744 bytes
- C6 full image: `slave/build-direct-safe/c6-espnow-full.bin`
- C6 SHA-256: `EF203FF1D9A510E768E629B0AC6D30C945530058C8ACA0F5354671D50D9FE8E2`
- C6 size: 1,249,440 bytes
- ESP-Hosted commit: `dd95bdf3316fc8c6110b387855033a26c0aa2447`
- ESP-IDF: v5.5.1

The C6 full image was erased and written at offset `0x0` over its UART ROM
downloader. Esptool verified the flash hash. After a complete board power cycle,
the unchanged historical P4 firmware initialized ESP-NOW successfully and its
test functions behaved as intended.

The full C6 image contains application SHA-256
`B82080CE0271C96720A3667195F544C9976D68A2907AC5B52C37BAB68E91512D`
byte-for-byte at offset `0x10000`.

## App-Only OTA Finding

The native P4 OTA module successfully transferred, finalized, and activated
C6 application images, but the C6 did not answer ESP-NOW bridge requests after
reboot. WLAN RPC remained operational. The same `B82080...` application works
when installed as part of the complete FTDI-flashed image.

This isolates the unresolved behavior to the C6 app-only OTA boot-slot/state
path, not the P4 MicroPython ESP-NOW integration or the C6 ESP-NOW application
code. Do not treat successful `ota_end()` and `ota_activate()` return values as
proof that the intended C6 application is running.

## Hardware Workflow

- P4 normal runtime port was COM17; P4 ROM download mode appeared as COM16.
- C6 UART ROM downloader was COM19 in the final recovery session.
- Park the P4 in manual download mode before direct C6 flashing.
- Connect UART TX, RX, and shared GND only; do not connect adapter VCC.
- Hold C6 IO9 to GND before powering the board to enter C6 ROM download mode.
- Remove IO9 from GND and fully power-cycle after a successful C6 write.

## Next Project Direction

Start from the hardware-tested P4 SD-card/ESP-NOW firmware and the modified
`esp32-p4-c6-espnow-enabler` repository branch `espnow-support` at commit
`6ecf6df055fa898a28739fc608dac9733bf0dcb2`.

Improve the enabler so it installs the complete known-good C6 flash state, or
adds a reliable post-reboot query that proves the running C6 partition and ELF
identity. Preserve the MicroPython fork changes based on commit `43eedf7` and
the SD-card branch changes through commit `b8eb920`.