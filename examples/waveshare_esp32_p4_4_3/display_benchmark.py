"""Measure forced full-screen LVGL refresh throughput on the Waveshare P4."""

import gc
import time

import display
import lvgl as lv
import task_handler


DURATION_MS = 30_000
WARMUP_FRAMES = 10
FRAME_PERIOD_MS = 16


def run_benchmark():
    disp = display.display._disp_drv
    width = disp.get_horizontal_resolution()
    height = disp.get_vertical_resolution()

    screen = lv.obj()
    screen.set_size(width, height)
    screen.set_pos(0, 0)
    screen.set_style_pad_all(0, 0)
    screen.set_style_border_width(0, 0)
    screen.set_style_radius(0, 0)

    marker = lv.obj(screen)
    marker.set_size(64, 64)
    marker.set_style_border_width(0, 0)
    marker.set_style_radius(0, 0)
    marker.set_style_bg_color(lv.color_hex(0x00FF00), 0)

    red = lv.color_hex(0xFF0000)
    blue = lv.color_hex(0x0000FF)
    handler = task_handler.TaskHandler._current_instance
    if handler is None:
        handler = task_handler.TaskHandler(duration=16)

    print("Starting forced-refresh display benchmark")
    print("Resolution: %dx%d" % (width, height))
    print("Double buffered:", disp.is_double_buffered())
    print("Duration: %d ms" % DURATION_MS)
    print("Target period: %d ms" % FRAME_PERIOD_MS)

    # Prevent the periodic handler from racing the explicit refresh calls.
    handler.deinit()
    lv.screen_load(screen)
    gc.collect()

    try:
        for frame in range(WARMUP_FRAMES):
            color = red if frame & 1 else blue
            screen.set_style_bg_color(color, 0)
            lv.refr_now(disp)
            time.sleep_ms(FRAME_PERIOD_MS)

        gc.collect()
        gc.disable()

        frames = 0
        total_us = 0
        minimum_us = None
        maximum_us = 0
        deadline_misses = 0
        use_red = False
        started_ms = time.ticks_ms()
        next_frame_ms = started_ms

        while time.ticks_diff(time.ticks_ms(), started_ms) < DURATION_MS:
            use_red = not use_red
            color = red if use_red else blue
            screen.set_style_bg_color(color, 0)

            marker.set_pos(
                (frames * 17) % (width - 64),
                (frames * 11) % (height - 64),
            )

            frame_started_us = time.ticks_us()
            lv.refr_now(disp)
            elapsed_us = time.ticks_diff(time.ticks_us(), frame_started_us)

            total_us += elapsed_us
            if minimum_us is None or elapsed_us < minimum_us:
                minimum_us = elapsed_us
            if elapsed_us > maximum_us:
                maximum_us = elapsed_us
            frames += 1

            next_frame_ms = time.ticks_add(next_frame_ms, FRAME_PERIOD_MS)
            remaining_ms = time.ticks_diff(next_frame_ms, time.ticks_ms())
            if remaining_ms > 0:
                time.sleep_ms(remaining_ms)
            else:
                deadline_misses += 1

        elapsed_ms = time.ticks_diff(time.ticks_ms(), started_ms)
    finally:
        gc.enable()
        task_handler.TaskHandler(duration=16)
        gc.collect()

    average_us = total_us // frames if frames else 0
    refreshes_per_second = frames * 1000 / elapsed_ms if elapsed_ms else 0

    print("\n" + "=" * 36)
    print("FORCED FULL-REFRESH RESULTS")
    print("=" * 36)
    print("Refreshes:       %d" % frames)
    print("Elapsed:         %d ms" % elapsed_ms)
    print("Update rate:     %.2f frames/s" % refreshes_per_second)
    print("Average latency: %.3f ms" % (average_us / 1000))
    print("Minimum latency: %.3f ms" % ((minimum_us or 0) / 1000))
    print("Maximum latency: %.3f ms" % (maximum_us / 1000))
    print("Deadline misses: %d" % deadline_misses)
    print("LVGL idle:       %d%%" % lv.timer_get_idle())
    print("=" * 36)


if __name__ == "__main__":
    run_benchmark()
