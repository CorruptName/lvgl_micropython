# Waveshare ESP32-P4 4.3-inch examples

These examples target the Waveshare ESP32-P4-WIFI6-Touch-LCD-4.3 firmware on
the `waveshare-esp32-p4-4.3` branch. Flash
`firmware-waveshare-esp32-p4-4.3-audio.bin` before running them.

Install `mpremote` on the computer connected to the board:

```powershell
python -m pip install mpremote
```

## LVGL touch button

`lvgl_button.py` creates a centered LVGL button. Each touch updates its label
and prints the number of presses. Run it from the repository root:

```powershell
python -m mpremote connect COM10 run examples/waveshare_esp32_p4_4_3/lvgl_button.py
```

From the MicroPython REPL, the same script can be pasted or saved to the board
and imported. The board's generated `display` module initializes the ST7701
display, GT911 touch controller, and LVGL task handler.

## Onboard speaker tone

`audio_tone.py` plays a 440 Hz sine wave for one second at volume 100:

```powershell
python -m mpremote connect COM10 run examples/waveshare_esp32_p4_4_3/audio_tone.py
```

To choose a different tone from the MicroPython REPL, import the function and
pass frequency in hertz, duration in milliseconds, and volume from 0 to 100:

```python
from audio_tone import play_tone
play_tone(frequency=880, duration_ms=500, volume=75)
```

Running the script plays the default tone. Importing it only provides the
`play_tone()` function.

The audio example uses the board's supported format: 16 kHz, signed 16-bit
stereo PCM with a 384x master clock. It disables the ES8311 codec and speaker
amplifier even if playback raises an exception.
