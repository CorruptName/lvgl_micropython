"""ESP-NOW device discovery example for the Waveshare ESP32-P4 4.3" display.

ESP-NOW has no built-in "scan" for peers, so discovery here is done by
periodically broadcasting a beacon and listening for beacons sent back by
any other board running this same script. Requires ESP-NOW support to be
enabled in firmware (MICROPY_PY_ESPNOW) and a second device to discover.
"""
import display  # Initializes the configured display, touch input, and task handler.
import lvgl as lv
import network
import espnow

BROADCAST = b"\xff\xff\xff\xff\xff\xff"
BEACON = b"ESPNOW-HELLO"
BEACON_PERIOD_MS = 1000

sta = None
e = None
my_mac = None
running = False
devices = {}  # mac -> rssi


def init_espnow():
    global sta, e, my_mac

    sta = network.WLAN(network.WLAN.IF_STA)
    sta.active(True)
    sta.disconnect()

    e = espnow.ESPNow()
    e.active(True)
    e.add_peer(BROADCAST)

    my_mac = sta.config("mac")


def format_mac(mac):
    return ":".join("%02x" % b for b in mac)


def refresh_device_list():
    if not devices:
        device_list.set_text("No devices found yet")
        return

    lines = []
    for mac, rssi in devices.items():
        lines.append("%s   RSSI: %s dBm" % (format_mac(mac), rssi))
    device_list.set_text("\n".join(lines))


def poll_timer_cb(timer):
    if not running:
        return

    e.send(BROADCAST, BEACON, False)

    mac, msg = e.recv(0)
    if mac is not None and msg == BEACON and mac != my_mac:
        is_new = mac not in devices
        devices[mac] = e.peers_table.get(mac, [None])[0]
        if is_new:
            print("Found ESP-NOW device:", format_mac(mac))
        refresh_device_list()
        status_label.set_text("%d device(s) found" % len(devices))


def start_scan(event):
    global running

    if running:
        return

    try:
        if e is None:
            init_espnow()
    except Exception as ex:
        status_label.set_text("ESP-NOW init failed")
        device_list.set_text(str(ex))
        print("ESP-NOW init failed:", ex)
        return

    running = True
    button_label.set_text("Stop")
    status_label.set_text("Scanning...")


def stop_scan(event):
    global running

    running = False
    button_label.set_text("Start Scan")
    status_label.set_text("Stopped")


def toggle_scan(event):
    if running:
        stop_scan(event)
    else:
        start_scan(event)


def clear_devices(event):
    devices.clear()
    refresh_device_list()
    status_label.set_text("List cleared")


screen = lv.screen_active()
screen.set_style_bg_color(lv.color_hex(0x18212B), 0)

heading = lv.label(screen)
heading.set_text("ESP-NOW Device Scanner")
heading.align(lv.ALIGN.CENTER, 0, -90)
heading.set_style_text_font(lv.font_montserrat_16, 0)

status_label = lv.label(screen)
status_label.set_text("Press Start Scan to begin")
status_label.align(lv.ALIGN.CENTER, 0, -50)
status_label.set_style_text_font(lv.font_montserrat_12, 0)

button = lv.button(screen)
button.set_size(220, 60)
button.align(lv.ALIGN.CENTER, 0, 0)
button.add_event_cb(toggle_scan, lv.EVENT.CLICKED, None)

button_label = lv.label(button)
button_label.set_text("Start Scan")
button_label.center()

clear_button = lv.button(screen)
clear_button.set_size(100, 40)
clear_button.align(lv.ALIGN.CENTER, 0, 60)
clear_button.add_event_cb(clear_devices, lv.EVENT.CLICKED, None)

clear_label = lv.label(clear_button)
clear_label.set_text("Clear")
clear_label.center()

device_list = lv.label(screen)
device_list.set_text("No devices found yet")
device_list.align(lv.ALIGN.CENTER, 0, 130)
device_list.set_style_text_font(lv.font_montserrat_12, 0)
device_list.set_width(340)
device_list.set_long_mode(lv.label.LONG_MODE.WRAP)

poll_timer = lv.timer_create(poll_timer_cb, BEACON_PERIOD_MS, None)

print("ESP-NOW scanner example ready")
