from micropython import const
from machine import Pin


I2C_ADDR = const(0x18)
BITS = const(8)

_REG_RESET = const(0x00)
_REG_CLK1 = const(0x01)
_REG_CLK2 = const(0x02)
_REG_CLK3 = const(0x03)
_REG_CLK4 = const(0x04)
_REG_CLK5 = const(0x05)
_REG_CLK6 = const(0x06)
_REG_CLK7 = const(0x07)
_REG_CLK8 = const(0x08)
_REG_SDP_IN = const(0x09)
_REG_SDP_OUT = const(0x0A)
_REG_SYSTEM0B = const(0x0B)
_REG_SYSTEM0C = const(0x0C)
_REG_SYSTEM0D = const(0x0D)
_REG_SYSTEM0E = const(0x0E)
_REG_SYSTEM10 = const(0x10)
_REG_SYSTEM11 = const(0x11)
_REG_SYSTEM12 = const(0x12)
_REG_SYSTEM13 = const(0x13)
_REG_SYSTEM14 = const(0x14)
_REG_ADC15 = const(0x15)
_REG_ADC16 = const(0x16)
_REG_ADC17 = const(0x17)
_REG_ADC1B = const(0x1B)
_REG_ADC1C = const(0x1C)
_REG_DAC31 = const(0x31)
_REG_DAC32 = const(0x32)
_REG_DAC37 = const(0x37)
_REG_GPIO44 = const(0x44)
_REG_GPIO45 = const(0x45)


class ES8311:
    def __init__(self, device, pa_pin, sample_rate=16000, mck_multiplier=384):
        if sample_rate != 16000 or mck_multiplier != 384:
            raise ValueError("ES8311 currently supports 16 kHz with 384x MCLK")

        self._device = device
        self._buffer = bytearray(1)
        self._pa = Pin(pa_pin, Pin.OUT, value=0)
        self._enabled = False
        self._open()
        self._configure_16k_16bit_stereo()
        self.set_volume(75)
        self.mute(True)

    def _read(self, register):
        self._device.read_mem(register, buf=self._buffer)
        return self._buffer[0]

    def _write(self, register, value):
        self._buffer[0] = value
        self._device.write_mem(register, self._buffer)

    def _update(self, register, mask, value):
        self._write(register, (self._read(register) & ~mask) | (value & mask))

    def _open(self):
        if self._read(_REG_SYSTEM0D) != 0xFA:
            self._write(_REG_SYSTEM0D, 0xFA)

        for register, value in (
            (_REG_GPIO44, 0x08),
            (_REG_GPIO44, 0x08),
            (_REG_CLK1, 0x30),
            (_REG_CLK2, 0x00),
            (_REG_CLK3, 0x10),
            (_REG_ADC16, 0x24),
            (_REG_CLK4, 0x10),
            (_REG_CLK5, 0x00),
            (_REG_SYSTEM0B, 0x00),
            (_REG_SYSTEM0C, 0x00),
            (_REG_SYSTEM10, 0x1F),
            (_REG_SYSTEM11, 0x7F),
            (_REG_RESET, 0x80),
            (_REG_CLK1, 0x3F),
            (_REG_SYSTEM13, 0x10),
            (_REG_ADC1B, 0x0A),
            (_REG_ADC1C, 0x6A),
            (_REG_GPIO44, 0x58),
        ):
            self._write(register, value)

        self._update(_REG_CLK6, 0x20, 0x00)

    def _configure_16k_16bit_stereo(self):
        self._update(_REG_SDP_IN, 0x1F, 0x0C)
        self._update(_REG_SDP_OUT, 0x1F, 0x0C)

        self._write(_REG_CLK2, 0x48)
        self._write(_REG_CLK5, 0x00)
        self._update(_REG_CLK3, 0x7F, 0x10)
        self._update(_REG_CLK4, 0x7F, 0x20)
        self._update(_REG_CLK7, 0x3F, 0x00)
        self._write(_REG_CLK8, 0xFF)
        self._update(_REG_CLK6, 0x1F, 0x03)

    def set_volume(self, volume):
        if not 0 <= volume <= 100:
            raise ValueError("volume must be between 0 and 100")
        if volume == 0:
            register_value = 0
        else:
            db_value = -50.0 + volume * 0.5 + 3.61
            register_value = int((db_value + 95.5) * 2.0)
        self._write(_REG_DAC32, min(register_value, 255))

    def mute(self, muted=True):
        self._update(_REG_DAC31, 0x60, 0x60 if muted else 0x00)

    def enable(self):
        if self._enabled:
            return

        for register, value in (
            (_REG_RESET, 0x80),
            (_REG_CLK1, 0x3F),
        ):
            self._write(register, value)

        self._update(_REG_SDP_IN, 0x40, 0x00)
        self._update(_REG_SDP_OUT, 0x40, 0x00)

        for register, value in (
            (_REG_ADC17, 0xBF),
            (_REG_SYSTEM0E, 0x02),
            (_REG_SYSTEM12, 0x00),
            (_REG_SYSTEM14, 0x1A),
            (_REG_SYSTEM0D, 0x01),
            (_REG_ADC15, 0x40),
            (_REG_DAC37, 0x08),
            (_REG_GPIO45, 0x00),
        ):
            self._write(register, value)

        self._pa.value(1)
        self.mute(False)
        self._enabled = True

    def disable(self):
        if not self._enabled:
            return
        self.mute(True)
        self._pa.value(0)
        self._enabled = False
