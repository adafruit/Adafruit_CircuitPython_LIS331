import time
import board
import busio
from adafruit_lis331 import *

i2c = busio.I2C(board.SCL, board.SDA)
# un-comment the sensor you are using
# lis = H3LIS331(i2c)
lis = LIS331HH(i2c)

# use a nice fast data rate to for maximum resolution
lis.data_rate = Rate.RATE_1000_HZ

# enable the high pass filter without a reference or offset
lis.enable_hpf(True, cutoff=RateDivisor.ODR_DIV_100, use_reference=False)

# you can also uncomment this section to set and use a reference to offset the measurements
# lis.hpf_reference = 50
# lis.enable_hpf(True, cutoff=RateDivisor.ODR_DIV_100, use_reference=True)


# watch in the serial plotter with the sensor still and you will see the
# z-axis value go from the normal around 9.8 with the filter off to near zero with it
# enabled. If you have a reference enabled and set, that will determind the center point.

# If you shake the sensor, you'll still see the acceleration values change! This is the
# Filter removing slow or non-changing values and letting through ones that move more quickly

while True:
    print(lis.acceleration)  # plotter friendly printing
    time.sleep(0.02)
