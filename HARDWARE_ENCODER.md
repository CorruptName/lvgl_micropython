# ESP32-P4 Hardware H.264 Encoder

The `h264` module exposes the ESP32-P4 hardware H.264 encoder to MicroPython. It
uses Espressif's `espressif/esp_h264` component and produces an Annex-B H.264
byte stream.

The module is built automatically for `ESP32_GENERIC_P4`. It is not available
on other targets.

## Creating an encoder

```python
import h264

encoder = h264.H264Encoder(
    480,
    800,
    fps=30,
    bitrate=2_000_000,
    gop=30,
    format=h264.RAW_FMT_O_UYY_E_VYY,
    qp_min=10,
    qp_max=40,
)
```

`width` and `height` must both be multiples of 16. The hardware accepts widths
from 80 through 1920 and heights from 80 through 2032.

Constructor options:

| Option | Default | Description |
| --- | ---: | --- |
| `fps`         | `30`                   | Maximum input frame rate, from 1 through 255             |
| `bitrate`     | `2000000`              | Target encoded bit rate in bits per second               |
| `gop`         | `30`                   | Distance between intra frames, from 1 through 255        |
| `format`      | `RAW_FMT_O_UYY_E_VYY`  | Raw input pixel format                                   |
| `qp_min`      | `10`                   | Minimum quantization parameter, from 0 through 51        |
| `qp_max`      | `40`                   | Maximum quantization parameter, from `qp_min` through 51 |

## Encoding frames

`encode(frame, pts=0)` accepts any readable buffer with exactly one packed raw
frame and returns one encoded frame as `bytes`. IDR output includes SPS and PPS
NAL units, so concatenating returned values creates an Annex-B elementary
stream.

```python
with open("capture.h264", "wb") as output:
    for pts, frame in enumerate(raw_frames):
        packet = encoder.encode(frame, pts)
        output.write(packet)

        if encoder.last_keyframe():
            print("keyframe", pts, encoder.last_frame_type())

encoder.close()
```

The frame type is one of `FRAME_TYPE_IDR`, `FRAME_TYPE_I`, or `FRAME_TYPE_P`.
Call `force_idr()` before `encode()` to make the next output frame an IDR frame:

```python
encoder.force_idr()
packet = encoder.encode(frame)
```

`close()` releases the hardware encoder and its frame buffers. It is safe to
call more than once. The object also closes during garbage collection, but
applications should close it explicitly because the internal buffers are
large.

## Raw input format

ESP32-P4 revisions older than 3.0, including revision 1.3, support only
`RAW_FMT_O_UYY_E_VYY`. This is packed YUV420 with alternating chroma lines:

```text
line 0: U Y Y U Y Y U Y Y ...
line 1: V Y Y V Y Y V Y Y ...
line 2: U Y Y U Y Y U Y Y ...
line 3: V Y Y V Y Y V Y Y ...
```

Its frame size is `width * height * 3 // 2` bytes. Width and height should be
even in addition to the encoder's multiple-of-16 requirement.

ESP32-P4 revision 3.0 and newer also support:

- `RAW_FMT_RGB565_LE`: little-endian RGB565, 2 bytes per pixel
- `RAW_FMT_BGR888`: BGR888, 3 bytes per pixel
- `RAW_FMT_VUY`: packed VUY, 3 bytes per pixel
- `RAW_FMT_UYVY`: packed UYVY, 2 bytes per pixel

Passing a format unsupported by the configured minimum silicon revision raises
`ValueError` when the encoder is created. A normal LVGL RGB565 framebuffer
therefore cannot be passed directly on revision 1.x or 2.x silicon; it must be
converted to `O_UYY_E_VYY` first.

## Memory and performance

The driver allocates two cache-aligned internal SRAM buffers, each equal to the
raw frame size. One holds a copy of the input and one receives encoded output.
For a 480 by 800 `O_UYY_E_VYY` frame, this reserves about 1.10 MiB in total:

```text
480 * 800 * 3 / 2 * 2 = 1,152,000 bytes
```

The input is copied into the aligned native buffer before each encode operation.
Encoding is synchronous: `encode()` does not return until the hardware finishes
the frame, and other Python code does not run during that call.

The documented hardware resolution range does not guarantee that both frame
buffers and the encoder's working memory will fit in internal SRAM. The
constructor raises `MemoryError` when the selected resolution cannot be
allocated alongside the rest of the running firmware.

Only one ESP32-P4 hardware encoder can actively use the shared H.264 peripheral
at a time. Encoded packet sizes vary by image content, bitrate, and frame type.

## Current limitations

- Hardware encoding only; no software encoder or decoder binding is provided.
- Single-stream encoding only.
- No direct LVGL framebuffer conversion or camera pipeline is included.
- No MP4, MPEG-TS, RTP, timestamps, or other container/muxing layer is added.
- Resolution and pixel format cannot be changed after construction.
- `encode()` allocates a new Python `bytes` object for every encoded frame.
- Runtime behavior still depends on the physical chip revision matching the
  firmware's configured minimum revision.

The `pts` value is passed through as the frame presentation timestamp. The
encoder does not assign a time base; the application or muxer must interpret it
consistently.

## Hardware test

The self-contained
[`h264_encoder_test.py`](examples/waveshare_esp32_p4_4_3/h264_encoder_test.py)
example generates packed `O_UYY_E_VYY` frames, writes a 90-frame Annex-B stream
to the Waveshare board's microSD card, exercises `force_idr()`, and checks the
reported frame types. No source media is required.

Run it from the repository root:

```powershell
python -m mpremote connect COM10 run examples/waveshare_esp32_p4_4_3/h264_encoder_test.py
```

After the script prints `H.264 hardware encoder test: PASS`, copy and inspect
the stream on the host:

```powershell
python -m mpremote connect COM10 fs cp :/sd/h264_encoder_test.h264 .
ffprobe -v error -show_streams h264_encoder_test.h264
ffmpeg -y -framerate 30 -i h264_encoder_test.h264 -c copy h264_encoder_test.mp4
```

This verifies encoder lifecycle, raw input handling, Annex-B output, normal
frame progression, forced IDR behavior, and sustained encoding. It does not
replace decoding the output on a second implementation: host playback catches
bitstream defects that packet and frame-type checks cannot detect.