import time

import display
import lvgl as lv


indev = display.indev
sample_count = 0
total_delta_us = 0
minimum_delta_us = None
maximum_delta_us = 0
previous_pressed_ms = None


def on_pressed(event):
    del event
    global sample_count, total_delta_us, minimum_delta_us, maximum_delta_us
    global previous_pressed_ms

    event_us = time.ticks_us()
    event_ms = time.ticks_ms()
    report_us = indev.last_report_us
    if report_us is None:
        print('LVGL PRESSED without a timestamped GT911 report')
        return

    delta_us = time.ticks_diff(event_us, report_us)
    sample_count += 1
    total_delta_us += delta_us
    minimum_delta_us = (
        delta_us if minimum_delta_us is None else min(minimum_delta_us, delta_us)
    )
    maximum_delta_us = max(maximum_delta_us, delta_us)
    average_delta_us = total_delta_us // sample_count
    idle_ms = (
        -1
        if previous_pressed_ms is None
        else time.ticks_diff(event_ms, previous_pressed_ms)
    )
    previous_pressed_ms = event_ms

    print(
        'GT911 report_us=%d LVGL pressed_us=%d delta_us=%d idle_ms=%d report=%d'
        % (report_us, event_us, delta_us, idle_ms, indev.report_count)
    )
    result.set_text(
        'Samples: %d\nRaw to LVGL: %d us\nMin / avg / max: %d / %d / %d us'
        % (
            sample_count,
            delta_us,
            minimum_delta_us,
            average_delta_us,
            maximum_delta_us,
        )
    )


screen = lv.screen_active()
screen.set_style_bg_color(lv.color_hex(0x16221D), 0)

target = lv.button(screen)
target.set_size(400, 620)
target.center()
target.add_event_cb(on_pressed, lv.EVENT.PRESSED, None)

heading = lv.label(target)
heading.set_text('Touch latency')
heading.align(lv.ALIGN.TOP_MID, 0, 80)

result = lv.label(target)
result.set_text('Waiting for touch\nGT911 poll interval: %d ms' % indev.poll_interval_ms)
result.set_text_align(lv.TEXT_ALIGN.CENTER)
result.center()

print('Touch latency test ready; GT911 poll interval:', indev.poll_interval_ms)
config = indev.firmware_config
print('GT911 low power control:', config.low_power_control)
print('GT911 refresh rate:', config.refresh_rate)
print('Set display.indev.poll_interval_ms at runtime to compare values.')
