# The MIT License (MIT)
#
# Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_lis331`
================================================================================

A library for the ST LIS331 family of high-g 3-axis accelerometers


* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `Adafruit LIS331HH Breakout <https://www.adafruit.com/products/45XX>`_
* `Adafruit H3LIS331 Breakout <https://www.adafruit.com/products/45XX>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

 * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
 * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_LIS331.git"

from struct import unpack_from
from time import sleep
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct
import adafruit_bus_device.i2c_device as i2c_device

_LIS331_DEFAULT_ADDRESS = 0x18  # If SDO/SA0 is 3V, its 0x19
_LIS331_CHIP_ID = 0x32  # The default response to WHO_AM_I for the H3LIS331 and LIS331HH
_LIS331_REG_WHOAMI = 0x0F  # Device identification register. [0, 0, 1, 1, 0, 0, 1, 1] */
_LIS331_REG_CTRL1 = 0x20  # Power mode, data rate, axis enable
_LIS331_REG_CTRL2 = 0x21  # Memory reboot, HPF config
_LIS331_REG_CTRL3 = 0x22  # Interrupt config, poarity, pin mode, latching, pin enable
_LIS331_REG_CTRL4 = 0x23  # BDU, Endianness, Range, SPI mode
_LIS331_REG_HP_FILTER_RESET = 0x25  # Dummy register to reset filter
_LIS331_REG_REFERENCE = 0x26  # HPF reference value
_LIS331_REG_OUT_X_L = 0x28  # X-axis acceleration data. Low value */

_G_TO_ACCEL = 9.80665


class ROByteArray:
    """
    Array of registers that are readable only.

    Based on the index, values are offset by the size of the structure.

    Values are FixNums that map to the values in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    .. note:: This assumes the device addresses correspond to 8-bit bytes. This is not suitable for
      devices with registers of other widths such as 16-bit.

    :param int register_address: The register address to begin reading the array from
    :param str struct_format: The struct format string for this register.
    :param int count: Number of elements in the array
    """

    def __init__(  # pylint: disable=too-many-arguments
        self, register_address, format_str, count
    ):

        self.buffer = bytearray(1 + count)
        self.buffer[0] = register_address
        self.format = format_str

    def __get__(self, obj, objtype=None):
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1)

        return unpack_from(self.format, self.buffer, 1)  # offset=1


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        "creates CV entires"
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value):
        "Returns true if the given value is a member of the CV"
        return value in cls.string


class LIS331HHRange(CV):
    """Options for ``range``"""


LIS331HHRange.add_values(
    (
        ("RANGE_6G", 0, 6, ((6 * 2) / 4096) * _G_TO_ACCEL),
        ("RANGE_12G", 1, 12, ((12 * 2) / 4096) * _G_TO_ACCEL),
        ("RANGE_24G", 3, 24, ((24 * 2) / 4096) * _G_TO_ACCEL),
    )
)


class H3LIS331Range(CV):
    """Options for ``range``"""


H3LIS331Range.add_values(
    (
        ("RANGE_100G", 0, 100, ((100 * 2) / 4096) * _G_TO_ACCEL),
        ("RANGE_200G", 1, 200, ((200 * 2) / 4096) * _G_TO_ACCEL),
        ("RANGE_400G", 3, 400, ((400 * 2) / 4096) * _G_TO_ACCEL),
    )
)


class Rate(CV):
    """Options for ``accelerometer_data_rate`` and ``gyro_data_rate``"""


Rate.add_values(
    (
        ("SHUTDOWN", 0, 0, None),
        ("RATE_50_HZ", 0x4, 50, None),
        ("RATE_100_HZ", 0x5, 100, None),
        ("RATE_400_HZ", 0x6, 400, None),
        ("RATE_1000_HZ", 0x7, 1000, None),
        ("RATE_LOWPOWER_0_5_HZ", 0x8, 0.5, None),
        ("RATE_LOWPOWER_1_HZ", 0xC, 1, None),
        ("RATE_LOWPOWER_2_HZ", 0x10, 2, None),
        ("RATE_LOWPOWER_5_HZ", 0x14, 5, None),
        ("RATE_LOWPOWER_10_HZ", 0x18, 10, None),
    )
)


class Mode(CV):
    """Options for ``accelerometer_data_rate`` and ``gyro_data_rate``"""


Mode.add_values(
    (
        ("SHUTDOWN", 0, "Shutdown", None),
        ("NORMAL", 1, "Normal", None),
        (
            "LOW_POWER",
            2,
            "Low Power",
            None,
        ),  # Low power is from 2-6 so checks against this should  be 'mode >=LIS331_MODE_LOW_POWER'
    )
)


class Frequency(CV):
    """Options for `lpf_cutoff`"""


Frequency.add_values(
    (
        ("FREQ_37_HZ", 0, 37, None),
        ("FREQ_74_HZ", 0, 74, None),
        ("FREQ_292_HZ", 0, 292, None),
        ("FREQ_780_HZ", 0, 37, None),
    )
)


class LIS331:
    """Base class for the LIS331 family of 3-axis accelerometers.
    **Cannot be instantiated directly**

        :param ~busio.I2C i2c_bus: The I2C bus the LIS331 is connected to.
        :param address: The I2C slave address of the sensor

    """

    _chip_id = ROUnaryStruct(_LIS331_REG_WHOAMI, "<B")
    _mode_and_odr_bits = RWBits(5, _LIS331_REG_CTRL1, 3)
    _power_mode_bits = RWBits(3, _LIS331_REG_CTRL1, 5)
    _data_rate_lpf_bits = RWBits(2, _LIS331_REG_CTRL1, 3)
    _range_bits = RWBits(2, _LIS331_REG_CTRL4, 4)
    CHIP_ID = None

    def __init__(self, i2c_bus, address=_LIS331_DEFAULT_ADDRESS):
        if (not isinstance(self, LIS331HH)) and (not isinstance(self, H3LIS331)):
            raise RuntimeError(
                "Base class LIS331 cannot be instantiated directly. Use LIS331HH or H3LIS331"
            )
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        if self._chip_id != _LIS331_CHIP_ID:
            raise RuntimeError(
                "Failed to find %s - check your wiring!" % self.__class__.__name__
            )
        self._range_class = None

    @property
    def lpf_cutoff(self):
        """The frequency above which signals will be filterd out"""
        if self.mode == Mode.NORMAL:  # pylint: disable=no-member
            raise RuntimeError(
                "lpf_cuttoff cannot be read while a NORMAL data rate is in use"
            )
        return self._data_rate_lpf_bits

    @lpf_cutoff.setter
    def lpf_cutoff(self, cutoff_freq):
        if not Frequency.is_valid(cutoff_freq):
            raise AttributeError("lpf_cutoff must be a `Frequency`")

        if self.mode == Mode.NORMAL:  # pylint: disable=no-member
            raise RuntimeError(
                "lpf_cuttoff cannot be set while a NORMAL data rate is in use"
            )

        self._data_rate_lpf_bits = cutoff_freq

    @property
    def data_rate(self):
        """Select the rate at which the accelerometer takes measurements. Must be a `Rate`"""
        # because both the power mode[pm] and data rate[dr] bits determine the data rate
        # we'll report the whole bunch
        return self._cached_data_rate

    @data_rate.setter
    def data_rate(self, new_rate_bits):
        if not Rate.is_valid(new_rate_bits):
            raise AttributeError("data_rate must be a `Rate`")
        # like `data_rate` we'll receive the whole group of pm/dr bits to determine what to be set
        # print("(entry)new_rate_bits", bin(new_rate_bits))
        new_mode, adjusted_rate_bits = self._mode_and_rate(new_rate_bits)
        # print("new mode:", bin(new_mode), "adjusted_rate_bits:", bin(adjusted_rate_bits))
        if new_mode == Mode.NORMAL:  # pylint: disable=no-member
            # print("Mode is NORMAL")
            # print("setting self._mode_and_odr_bits to new_rate_bits", bin(new_rate_bits))
            self._mode_and_odr_bits = new_rate_bits
        else:
            # print("Mode is ", Mode.string[new_mode], "and not NORMAL")
            # print("setting self._power_mode_bits to new_mode", bin(new_mode))
            self._power_mode_bits = new_mode

        self._cached_data_rate = new_mode << 2 | new_rate_bits

    @property
    def mode(self):
        """The `Mode` power mode that the sensor is set to, as determined by the current
        `data_rate`. To set the mode, use `data_rate` and the approprite `Rate`"""
        mode_bits = self._mode_and_rate()[0]
        return mode_bits

    def _mode_and_rate(self, data_rate=None):
        if data_rate is None:
            data_rate = self._cached_data_rate
        # pylint: disable=no-member
        pm_value = (data_rate & 0x1C) >> 2
        dr_value = data_rate & 0x3
        if pm_value is Mode.LOW_POWER:
            dr_value = 0
        return (pm_value, dr_value)

    @property
    def range(self):
        """Adjusts the range of values that the sensor can measure, Note that larger ranges will be
         less accurate. Must be a `H3LIS331Range` or `LIS331HHRange` """
        return self._range_bits

    @range.setter
    def range(self, new_range):
        if not self._range_class.is_valid(new_range):  # pylint: disable=no-member
            raise AttributeError(
                "range must be a `%s`" % self._range_class.__qualname__
            )
        self._range_bits = new_range
        self._cached_accel_range = new_range
        sleep(0.010)  # give time for the new rate to settle

    _raw_acceleration = ROByteArray((_LIS331_REG_OUT_X_L | 0x80), "<hhh", 6)

    @property
    def acceleration(self):
        """The x, y, z acceleration values returned in a 3-tuple and are in m / s ^ 2."""

        raw_acceleration_bytes = self._raw_acceleration

        return (
            self._scale_acceleration(raw_acceleration_bytes[0]),
            self._scale_acceleration(raw_acceleration_bytes[1]),
            self._scale_acceleration(raw_acceleration_bytes[2]),
        )

    def _scale_acceleration(self, value):
        # The measurements are 12 bits left justified to preserve the sign bit
        right_justified = value >> 4
        lsb_value = self._range_class.lsb[self._cached_accel_range]
        # print("v:", value, "cr:", self._cached_accel_range, "l:", lsb_value)
        return right_justified * lsb_value


class LIS331HH(LIS331):
    """Driver for the LIS331HH 3-axis high-g accelerometer.

        :param ~busio.I2C i2c_bus: The I2C bus the LIS331 is connected to.
        :param address: The I2C slave address of the sensor

    """

    def __init__(self, i2c_bus, address=_LIS331_DEFAULT_ADDRESS):
        # pylint: disable=no-member
        super().__init__(i2c_bus, address)
        self._range_class = LIS331HHRange
        self.data_rate = Rate.RATE_1000_HZ
        self.range = LIS331HHRange.RANGE_24G


class H3LIS331(LIS331):
    """Driver for the H3LIS331 3-axis high-g accelerometer.

        :param ~busio.I2C i2c_bus: The I2C bus the LIS331 is connected to.
        :param address: The I2C slave address of the sensor

    """

    def __init__(self, i2c_bus, address=_LIS331_DEFAULT_ADDRESS):
        # pylint: disable=no-member
        super().__init__(i2c_bus, address)
        self._range_class = H3LIS331Range
        self.data_rate = Rate.RATE_1000_HZ
        self.range = H3LIS331Range.RANGE_400G
