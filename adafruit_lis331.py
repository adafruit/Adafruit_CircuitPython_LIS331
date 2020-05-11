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

# from adafruit_register.i2c_bits import RWBits
# from adafruit_register.i2c_bit import RWBit


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


class AccelRange(CV):
    """Options for ``accelerometer_range``"""


AccelRange.add_values(
    (
        ("RANGE_2G", 0, 2, 0.061),
        ("RANGE_16G", 1, 16, 0.488),
        ("RANGE_4G", 2, 4, 0.122),
        ("RANGE_8G", 3, 8, 0.244),
    )
)


class LIS331HHRange(CV):
    """Options for ``accelerometer_range``"""


LIS331HHRange.add_values(
    (
        ("RANGE_2G", 0, 2, 0.061),
        ("RANGE_16G", 1, 16, 0.488),
        ("RANGE_4G", 2, 4, 0.122),
        ("RANGE_8G", 3, 8, 0.244),
    )
)


class H3LIS331Range(CV):
    """Options for ``range``"""


H3LIS331Range.add_values(
    (
        ("RANGE_125_DPS", 125, 125, 4.375),
        ("RANGE_250_DPS", 0, 250, 8.75),
        ("RANGE_500_DPS", 1, 500, 17.50),
        ("RANGE_1000_DPS", 2, 1000, 35.0),
        ("RANGE_2000_DPS", 3, 2000, 70.0),
        ("RANGE_4000_DPS", 4000, 4000, 140.0),
    )
)


class Rate(CV):
    """Options for ``accelerometer_data_rate`` and ``gyro_data_rate``"""


Rate.add_values(
    (
        ("RATE_SHUTDOWN", 0, 0, None),
        ("RATE_12_5_HZ", 1, 12.5, None),
        ("RATE_26_HZ", 2, 26.0, None),
        ("RATE_52_HZ", 3, 52.0, None),
        ("RATE_104_HZ", 4, 104.0, None),
        ("RATE_208_HZ", 5, 208.0, None),
        ("RATE_416_HZ", 6, 416.0, None),
        ("RATE_833_HZ", 7, 833.0, None),
        ("RATE_1_66K_HZ", 8, 1066.0, None),
        ("RATE_3_33K_HZ", 9, 3033.0, None),
        ("RATE_6_66K_HZ", 10, 6066.0, None),
        ("RATE_1_6_HZ", 11, 1.6, None),
    )
)

# /**
#  * @brief Mode Options
#  *
#  */
# typedef enum {
#   LIS331_MODE_SHUTDOWN,
#   LIS331_MODE_NORMAL,
#   LIS331_MODE_LOW_POWER // Low power is from 2-6 so checks against this should
#                         // be 'mode >=LIS331_MODE_LOW_POWER'
# } lis331_mode_t;
# /*!
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


class LIS331:
    """Driver for the LIS331 Family of 3-axis accelerometers.

        :param ~busio.I2C i2c_bus: The I2C bus the LIS331 is connected to.
        :param address: The I2C slave address of the sensor

    """

    _chip_id = ROUnaryStruct(_LIS331_REG_WHOAMI, "<B")
    CHIP_ID = None

    def __init__(self, i2c_bus, address=_LIS331_DEFAULT_ADDRESS):
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        # if self.CHIP_ID is None:
        #     raise AttributeError("LSM6DS Parent Class cannot be directly instantiated")
        if self._chip_id != _LIS331_CHIP_ID:
            raise RuntimeError(
                "Failed to find %s - check your wiring!" % self.__class__.__name__
            )
        print("past chip ID check")

    @property
    def acceleration(self):
        """The x, y, z acceleration values returned in a 3-tuple and are in m / s ^ 2."""
        return (0, 0, 9.8)
