"""Visual regression test for text and solid-object rendering artifacts."""

import time

import display
import lvgl as lv


screen = lv.screen_active()
screen.set_style_bg_color(lv.color_hex(0x101820), 0)

heading = lv.label(screen)
heading.set_text("ESP32-P4 PPA rendering test")
heading.align(lv.ALIGN.TOP_MID, 0, 24)

status = lv.label(screen)
status.set_width(440)
status.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
status.align(lv.ALIGN.TOP_MID, 0, 78)

moving_label = lv.label(screen)
moving_label.set_text("Moving text: ABC 0123456789")
moving_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

moving_box = lv.obj(screen)
moving_box.set_size(96, 72)
moving_box.set_style_radius(0, 0)
moving_box.set_style_border_width(0, 0)
moving_box.set_style_bg_color(lv.color_hex(0x00A0FF), 0)

static_boxes = []
for index, color in enumerate((0xFF3030, 0x30FF30, 0x3030FF, 0xFFFF30)):
    box = lv.obj(screen)
    box.set_size(90, 64)
    box.set_pos(15 + index * 115, 690)
    box.set_style_radius(0, 0)
    box.set_style_border_width(0, 0)
    box.set_style_bg_color(lv.color_hex(color), 0)
    static_boxes.append(box)

frame = 0
started = time.ticks_ms()


def update(timer):
    global frame

    x = (frame * 7) % 360
    y = 150 + (frame * 5) % 440
    moving_label.set_pos(20 + x, y)
    moving_box.set_pos(20 + ((frame * 11) % 350), 570)

    status.set_text(
        "Frame %d   elapsed %.1fs\n"
        "Watch for displaced fills, stale glyphs, tearing, or mirrored blocks"
        % (frame, time.ticks_diff(time.ticks_ms(), started) / 1000)
    )
    frame += 1


update_timer = lv.timer_create(update, 16, None)
print("Display artifact test running")
