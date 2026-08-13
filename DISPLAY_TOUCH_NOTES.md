# Display and Touch Notes

This document collects display and touch-controller details for the
ESP32-P4-WIFI6-Touch-LCD-4.3 board. It is intended to be extended as more
hardware information is confirmed.

The values in the Display Configuration and GT911 Board Configuration sections
come from `examples/esp-idf/08_lvgl_demo_v9`. Register-level GT911 information
is identified separately because the external `esp_lcd_touch_gt911` component
source is not checked into this repository.

## Display Configuration

### Controller and Interface

- LCD controller: ST7701
- Interface: MIPI-DSI video with DBI commands
- DSI host bus: 0
- DSI virtual channel: 0
- DSI data lanes: 2
- DSI lane bitrate: 500 Mbps per lane
- DBI command width: 8 bits
- DBI parameter width: 8 bits
- Active resolution: 480 x 800
- Pixel format: RGB565 in the DPI configuration
- Color order: RGB

Source:

- [`display.h`](examples/esp-idf/08_lvgl_demo_v9/components/esp32_p4_wifi6_touch_lcd_4_3/include/bsp/display.h)
- [`esp32_p4_wifi6_touch_lcd_4_3.c`](examples/esp-idf/08_lvgl_demo_v9/components/esp32_p4_wifi6_touch_lcd_4_3/esp32_p4_wifi6_touch_lcd_4_3.c)

### DPI Timing

| Parameter | Value |
| --- | ---: |
| Pixel clock | 30 MHz |
| Horizontal active area | 480 pixels |
| Horizontal back porch | 42 pixels |
| HSYNC pulse width | 12 pixels |
| Horizontal front porch | 42 pixels |
| Horizontal total | 576 pixels |
| Vertical active area | 800 lines |
| Vertical back porch | 2 lines |
| VSYNC pulse width | 8 lines |
| Vertical front porch | 60 lines |
| Vertical total | 870 lines |
| Calculated refresh rate | approximately 59.87 Hz |

The calculated refresh rate is:

```text
30,000,000 / ((480 + 42 + 12 + 42) * (800 + 2 + 8 + 60)) = 59.87 Hz
```

No explicit HSYNC, VSYNC, DE, or pixel-clock polarity flags are set, so the
ESP-IDF driver defaults are used.

### Validated Release Rendering Profile

Both installer/release Waveshare configurations deliberately use:

- `LV_USE_PPA=0` and `LV_USE_PPA_IMG=0`
- 64-byte LVGL draw-buffer and memory alignment
- Two full-screen DSI framebuffers
- Buffer release on ESP-IDF `on_refresh_done`, not
  `on_color_trans_done`, so LVGL cannot redraw a buffer still being scanned
- A 16 ms LVGL task-handler period to service the approximately 60 Hz panel

The bundled LVGL 9.4 PPA renderer produced visible solid-fill corruption on
physical hardware and is not enabled in release firmware. Do not enable PPA or
change the DSI timing/buffer-completion behavior without repeated full-screen
redraw, moving-text/object, touch, and long-duration artifact tests on the
actual Waveshare board.

The standard and ESP-NOW profiles are respectively:

- `display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3-Standard.toml`
- `display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3.toml`

### D-PHY Power

- Regulator: ESP32-P4 on-chip LDO
- LDO channel: 3 (`LDO_VO3`)
- Voltage: 2500 mV
- Connected rail: `VDD_MIPI_DPHY`

The BSP acquires this LDO channel before creating the MIPI-DSI bus.

### Backlight

The backlight is controlled directly by LEDC PWM. It is not controlled through
an I2C peripheral.

| Parameter | Value |
| --- | --- |
| Backlight GPIO | GPIO 26 |
| PWM peripheral | LEDC, low-speed mode |
| PWM timer | Timer 1 |
| PWM channel | `CONFIG_BSP_DISPLAY_BRIGHTNESS_LEDC_CH` |
| PWM frequency | 5 kHz |
| PWM resolution | 10 bits (0-1023) |
| Output inversion | Enabled |
| Brightness API range | 0-100 percent |

`bsp_display_backlight_on()` requests 100 percent brightness and
`bsp_display_backlight_off()` requests 0 percent. The BSP maps the requested
percentage linearly onto the 10-bit LEDC duty value.

### Reset

- ST7701 LCD reset: GPIO 27
- Reset is performed through `esp_lcd_panel_reset()` before panel
  initialization.

### ST7701 Initialization Commands

Each row contains the command byte, its parameter bytes, and the delay after
the command. A dash means that the command has no parameters.

| Command | Parameters | Delay |
| --- | --- | ---: |
| `FF` | `77 01 00 00 13` | 0 ms |
| `EF` | `08` | 0 ms |
| `FF` | `77 01 00 00 10` | 0 ms |
| `C0` | `63 00` | 0 ms |
| `C1` | `0D 02` | 0 ms |
| `C2` | `17 08` | 0 ms |
| `CC` | `10` | 0 ms |
| `B0` | `40 C9 94 0E 10 05 0B 09 08 26 04 52 10 69 6B 69` | 0 ms |
| `B1` | `40 D2 98 0C 92 07 09 08 07 25 02 0E 0C 6E 78 55` | 0 ms |
| `FF` | `77 01 00 00 11` | 0 ms |
| `B0` | `5D` | 0 ms |
| `B1` | `4E` | 0 ms |
| `B2` | `87` | 0 ms |
| `B3` | `80` | 0 ms |
| `B5` | `4E` | 0 ms |
| `B7` | `85` | 0 ms |
| `B8` | `21` | 0 ms |
| `B9` | `10 1F` | 0 ms |
| `BB` | `03` | 0 ms |
| `BC` | `00` | 0 ms |
| `C1` | `78` | 0 ms |
| `C2` | `78` | 0 ms |
| `D0` | `88` | 0 ms |
| `E0` | `00 3A 02` | 0 ms |
| `E1` | `04 A0 00 A0 05 A0 00 A0 00 40 40` | 0 ms |
| `E2` | `30 00 40 40 32 A0 00 A0 00 A0 00 A0 00` | 0 ms |
| `E3` | `00 00 33 33` | 0 ms |
| `E4` | `44 44` | 0 ms |
| `E5` | `09 2E A0 A0 0B 30 A0 A0 05 2A A0 A0 07 2C A0 A0` | 0 ms |
| `E6` | `00 00 33 33` | 0 ms |
| `E7` | `44 44` | 0 ms |
| `E8` | `08 2D A0 A0 0A 2F A0 A0 04 29 A0 A0 06 2B A0 A0` | 0 ms |
| `EB` | `00 00 4E 4E 00 00 00` | 0 ms |
| `EC` | `08 01` | 0 ms |
| `ED` | `B0 2B 98 A4 56 7F FF FF FF FF F7 65 4A 89 B2 0B` | 0 ms |
| `EF` | `08 08 08 45 3F 54` | 0 ms |
| `FF` | `77 01 00 00 00` | 0 ms |
| `11` | - | 120 ms |
| `29` | - | 0 ms |

## GT911 Board Configuration

### Wiring and Bus

| Signal or setting | Value |
| --- | --- |
| Controller | Goodix GT911 |
| SDA | GPIO 7 |
| SCL | GPIO 8 |
| Reset | GPIO 23 |
| Interrupt | Not connected (`GPIO_NUM_NC`) |
| Default I2C controller | I2C1 |
| Default I2C speed | 400 kHz |
| Optional I2C speed | 100 kHz |
| I2C probe timeout | 100 ms |

The touch reset is configured as active low. A source comment says that touch
reset is shared with LCD reset, but the actual pin definitions are separate:
GT911 reset is GPIO 23 and LCD reset is GPIO 27.

The I2C bus is shared with other board peripherals. A standalone GT911 driver
should accept an existing bus handle rather than assuming exclusive ownership.

### Address Detection

The BSP probes both supported 7-bit GT911 addresses:

1. `0x5D`
2. `0x14`

It uses the first address that responds. Because the interrupt pin is not
connected on this board, software cannot perform the usual reset/INT sequence
to select an address. A replacement driver should probe both addresses.

### Coordinates and Orientation

- Logical X range: 0-479
- Logical Y range: 0-799
- Maximum configured dimensions: 480 x 800
- Swap X/Y: disabled
- Mirror X: disabled
- Mirror Y: disabled

The example passes these orientation flags through to the ESP-IDF GT911 touch
component, so no board-specific coordinate transformation is needed for the
default portrait orientation.

### Polling

The GT911 interrupt signal is not connected, so touch input must be polled. The
USB extended-screen example warns that reading the GT911 more frequently can
produce false reports and waits 20 ms between reads. Use a polling interval of
at least 20 ms (at most approximately 50 reads per second) as the initial safe
setting.

Source: [`app_touch.c`](examples/esp-idf/12_usb_extend_screen/main/app_touch.c)

## GT911 Register-Level Driver Notes

The repository declares `esp_lcd_touch_gt911` version `^1` as an external IDF
component, but does not contain that component's source. The following items are
standard GT911 protocol details and should be checked against the exact GT911
datasheet or component version before finalizing a new driver.

| Register | Typical purpose |
| --- | --- |
| `0x8047` | Start of configuration block |
| `0x8140` | Four-byte ASCII product ID |
| `0x8144` | Firmware version |
| `0x8146` | Configured X resolution |
| `0x8148` | Configured Y resolution |
| `0x814E` | Touch status |
| `0x814F` | First touch-point record |

Typical transaction behavior:

- Register addresses are 16-bit and sent most-significant byte first.
- Multi-byte coordinate fields are little-endian.
- Bit 7 of touch status (`0x814E`) indicates that a new report is ready.
- The low nibble of touch status contains the number of active points.
- A touch-point record is eight bytes and includes track ID, X, Y, and contact
  size.
- GT911 commonly supports up to five simultaneous touch points.
- After consuming a ready report, write `0x00` to `0x814E` to acknowledge it.
- Clear a ready zero-point report as well so release events are handled.
- Reject or clear reports with an invalid point count.

A basic polling sequence is:

```text
read status from 0x814E
if status bit 7 is clear:
    no new report
else:
    count = status & 0x0F
    if count is valid and nonzero:
        read count * 8 bytes starting at 0x814F
        decode track ID, X, Y, and contact size
    write 0x00 to 0x814E
wait until at least 20 ms from the previous poll
```

Avoid rewriting the GT911 configuration block until the board's current config
version, checksum, and expected update procedure have been verified. The
controller already reports coordinates suitable for the 480 x 800 panel.

## Open Items

The following details would be useful additions when they are measured or
confirmed from authoritative documentation:

- Exact LCD panel module manufacturer and panel part number
- ST7701 command meanings for this panel-specific initialization table
- Explicit DPI signal polarities used by the ESP-IDF defaults
- GT911 product ID, firmware version, and configuration version read from the
  physical board
- GT911 configuration checksum and complete configuration block
- Confirmed hardware strap that selects `0x5D` or `0x14` on this board revision
- Touch reset pulse timing observed or required on this board
- Maximum reliable touch polling rate under application load