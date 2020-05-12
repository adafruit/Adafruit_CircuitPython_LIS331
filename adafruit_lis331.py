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

# imports

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_LIS331.git"

# from time import sleep
import adafruit_bus_device.i2c_device as i2c_device
from adafruit_register.i2c_struct import ROUnaryStruct  # , Struct

from adafruit_register.i2c_bits import RWBits, ROByteArray

# from adafruit_register.i2c_bit import RWBit

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
    """Options for ``accelerometer_range``"""


LIS331HHRange.add_values(
    (
        ("RANGE_6G", 0, 6, ((6 * 2) / 4096) * _G_TO_ACCEL),
        ("RANGE_12G", 1, 12, ((12 * 2) / 4096) * _G_TO_ACCEL),
        ("RANGE_24G", 3, 24, ((24 * 2) / 4096) * _G_TO_ACCEL),
    )
)


class Rate(CV):
    """Options for ``accelerometer_data_rate`` and ``gyro_data_rate``"""


Rate.add_values(
    (
        ("RATE_SHUTDOWN", 0, 0, None),
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


class LIS331:
    """Driver for the LIS331 Family of 3-axis accelerometers.

        :param ~busio.I2C i2c_bus: The I2C bus the LIS331 is connected to.
        :param address: The I2C slave address of the sensor

    """

    _chip_id = ROUnaryStruct(_LIS331_REG_WHOAMI, "<B")
    _mode_and_odr = RWBits(5, _LIS331_REG_CTRL1, 3)
    CHIP_ID = None

    def __init__(self, i2c_bus, address=_LIS331_DEFAULT_ADDRESS):
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        if self._chip_id != _LIS331_CHIP_ID:
            raise RuntimeError(
                "Failed to find %s - check your wiring!" % self.__class__.__name__
            )

        self.data_rate = Rate.RATE_1000_HZ  # pylint: disable=no-member
        self._cached_accel_range = LIS331HHRange.RANGE_6G  # pylint: disable=no-member

    @property
    def data_rate(self):
        """Select the rate at which the accelerometer takes measurements. Must be a `Rate`"""
        return 1

    @data_rate.setter
    def data_rate(self, value):
        self._mode_and_odr = value

    def _mode(self, data_rate):
        # pylint: disable=no-member
        pm_value = (data_rate & 0x1C) >> 2
        if pm_value >= Mode.LOW_POWER:
            return Mode.LOW_POWER

        return pm_value

    _raw_acceleration = ROByteArray(6, (_LIS331_REG_OUT_X_L | 0x80), "<hhh")

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
        # The measurements are 12 bits left justified to preserve the sign
        right_justified = value >> 4
        return right_justified * LIS331HHRange.lsb[self._cached_accel_range]

        # Adafruit_BusIO_Register _ctrl1 = Adafruit_BusIO_Register(
        #     i2c_dev, spi_dev, ADDRBIT8_HIGH_TOREAD, LIS331_REG_CTRL1, 1);
        # _ctrl1.write(0x07); // enable all axes, normal mode

        # setDataRate(LIS331_DATARATE_1000_HZ);
        # setRange(H3LIS331_RANGE_400_G);

        # void Adafruit_LIS331::setDataRate(lis331_data_rate_t data_rate) {
        # int8_t dr_value = 0;
        # int8_t pm_value = 0;

        # lis331_mode_t new_mode = getMode(data_rate);
        # Adafruit_BusIO_Register _ctrl1 = Adafruit_BusIO_Register(
        #     i2c_dev, spi_dev, ADDRBIT8_HIGH_TOREAD, LIS331_REG_CTRL1, 1);
        # Adafruit_BusIO_RegisterBits pm_bits =
        #     Adafruit_BusIO_RegisterBits(&_ctrl1, 3, 5);

        # switch (new_mode) {
        # case LIS331_MODE_SHUTDOWN:
        #     break;

        # case LIS331_MODE_LOW_POWER: // ODR bits are in CTRL1[7:5] (PM)
        #     pm_value = ((data_rate & 0x1C)) >> 2;
        #     break;

        # case LIS331_MODE_NORMAL: // ODR bits are in CTRL1[4:3] (DR)
        #     pm_value = ((data_rate & 0x1C)) >> 2;
        #     dr_value = (data_rate & 0x7);

        #     // only Normal mode uses DR to set ODR, so we can set it here
        #     Adafruit_BusIO_RegisterBits dr_bits =
        #         Adafruit_BusIO_RegisterBits(&_ctrl1, 2, 3);
        #     dr_bits.write(dr_value);
        #     break;
        # }

        # pm_bits.write(pm_value);
        # }

        # /*!
        # *   @brief  Gets the data rate for the LIS331 (affects power consumption)
        # *   @return Returns Data Rate value
        # */
        # lis331_data_rate_t Adafruit_LIS331::getDataRate(void) {
        # Adafruit_BusIO_Register _ctrl1 = Adafruit_BusIO_Register(
        #     i2c_dev, spi_dev, ADDRBIT8_HIGH_TOREAD, LIS331_REG_CTRL1, 1);
        # Adafruit_BusIO_RegisterBits pm_dr_bits =
        #     Adafruit_BusIO_RegisterBits(&_ctrl1, 5, 3);
        # return (lis331_data_rate_t)pm_dr_bits.read();
        # }

        # /**
        # * @brief  Return the current power mode from the current data rate
        # * @return lis331_mode_t The currently set power mode
        # */
        # lis331_mode_t Adafruit_LIS331::getMode(void) {
        # lis331_data_rate_t current_rate = getDataRate();
        # return getMode(current_rate);
        # }

        # /**
        # * @brief Return the current power mode from a given data rate value
        # *
        # * @param data_rate The `lis331_data_rate_t` to return the `lis331_mode_t` for
        # * @return lis331_mode_t
        # */
        # lis331_mode_t Adafruit_LIS331::getMode(lis331_data_rate_t data_rate) {
        # uint8_t pm_value = (data_rate & 0x1C) >> 2;
        # if (pm_value >= LIS331_MODE_LOW_POWER) {
        #     return LIS331_MODE_LOW_POWER;
        # }
        # return (lis331_mode_t)pm_value;
        # }
