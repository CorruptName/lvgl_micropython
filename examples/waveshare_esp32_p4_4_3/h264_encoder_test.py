import gc
import machine
import os
import time

import h264


MOUNT_POINT = "/sd"
OUTPUT_PATH = MOUNT_POINT + "/h264_encoder_test.h264"
WIDTH = 320
HEIGHT = 240
FPS = 30
FRAME_COUNT = 90
FORCED_IDR_FRAME = 45


def fill_test_frame(frame, frame_number):
    row_size = WIDTH * 3 // 2
    stripe_start = (frame_number * 6) % WIDTH

    for y in range(HEIGHT):
        row_start = y * row_size
        chroma = 96 + ((y // 30 + frame_number // 15) % 3) * 32

        for x in range(0, WIDTH, 2):
            offset = row_start + x * 3 // 2
            distance = (x - stripe_start) % WIDTH
            luminance = 220 if distance < 48 else 32 + (x * 160 // WIDTH)
            frame[offset] = chroma
            frame[offset + 1] = luminance
            frame[offset + 2] = luminance


def has_annex_b_start_code(packet):
    return packet.find(b"\x00\x00\x01") >= 0


def test_h264_encoder(output_path=OUTPUT_PATH):
    encoder = None
    frame = bytearray(WIDTH * HEIGHT * 3 // 2)
    frame_types = {h264.FRAME_TYPE_IDR: 0, h264.FRAME_TYPE_I: 0, h264.FRAME_TYPE_P: 0}
    encoded_bytes = 0
    encode_time_us = 0

    gc.collect()
    free_before = gc.mem_free()

    try:
        encoder = h264.H264Encoder(
            WIDTH,
            HEIGHT,
            fps=FPS,
            bitrate=800_000,
            gop=FPS,
            format=h264.RAW_FMT_O_UYY_E_VYY,
        )

        with open(output_path, "wb") as output:
            for frame_number in range(FRAME_COUNT):
                fill_test_frame(frame, frame_number)

                if frame_number == FORCED_IDR_FRAME:
                    encoder.force_idr()

                started_us = time.ticks_us()
                packet = encoder.encode(frame, frame_number * 90_000 // FPS)
                encode_time_us += time.ticks_diff(time.ticks_us(), started_us)

                if not packet:
                    raise RuntimeError("encoder returned an empty packet")
                if not has_annex_b_start_code(packet):
                    raise RuntimeError("packet does not contain an Annex-B start code")

                frame_type = encoder.last_frame_type()
                if frame_type not in frame_types:
                    raise RuntimeError("encoder returned an unknown frame type: {}".format(frame_type))
                if frame_number == FORCED_IDR_FRAME and frame_type != h264.FRAME_TYPE_IDR:
                    raise RuntimeError("force_idr() did not produce an IDR frame")
                if encoder.last_keyframe() != (
                    frame_type == h264.FRAME_TYPE_IDR or frame_type == h264.FRAME_TYPE_I
                ):
                    raise RuntimeError("last_keyframe() disagrees with last_frame_type()")

                frame_types[frame_type] += 1
                encoded_bytes += output.write(packet)

                if frame_number % FPS == 0 or frame_number == FRAME_COUNT - 1:
                    print(
                        "frame {}/{}: {} bytes, type {}".format(
                            frame_number + 1, FRAME_COUNT, len(packet), frame_type
                        )
                    )

        if frame_types[h264.FRAME_TYPE_IDR] < 2:
            raise RuntimeError("expected initial and forced IDR frames")

        average_ms = encode_time_us / FRAME_COUNT / 1000
        encoder_fps = FRAME_COUNT * 1_000_000 / encode_time_us
        print("Output:", output_path)
        print("Encoded bytes:", encoded_bytes)
        print("Frame counts: IDR={}, I={}, P={}".format(
            frame_types[h264.FRAME_TYPE_IDR],
            frame_types[h264.FRAME_TYPE_I],
            frame_types[h264.FRAME_TYPE_P],
        ))
        print("Average hardware encode time: {:.2f} ms".format(average_ms))
        print("Hardware encode throughput: {:.2f} fps".format(encoder_fps))
        print("Native encoder allocation observed by GC: {} bytes".format(free_before - gc.mem_free()))
        print("H.264 hardware encoder test: PASS")
    finally:
        if encoder is not None:
            encoder.close()


def run_sdcard_test():
    sdcard = None
    mounted = False

    try:
        sdcard = machine.SDCard(slot=0, width=4, freq=40_000_000, ldo_chan=4)
        os.mount(sdcard, MOUNT_POINT)
        mounted = True
        test_h264_encoder()
    finally:
        if mounted:
            os.umount(MOUNT_POINT)
        if sdcard is not None:
            sdcard.deinit()


if __name__ == "__main__":
    run_sdcard_test()