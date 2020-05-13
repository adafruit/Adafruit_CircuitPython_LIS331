import time
import board
import busio
from adafruit_lis331 import *

i2c = busio.I2C(board.SCL, board.SDA)
# un-comment the sensor you are using
# lis = H3LIS331(i2c)
lis = LIS331HH(i2c)

lis.data_rate = Rate.RATE_LOWPOWER_10_HZ
print("Rate is %sHz" % Rate.string[lis.data_rate])

lis.lpf_cutoff = Frequency.FREQ_37_HZ
print("LPF cutoff frequency is %sHz" % Frequency.string[lis.lpf_cutoff])

# un-comment the range for the sensor you are using
# lis.range = H3LIS331Range.RANGE_100G
# range_string = H3LIS331Range.string[lis.range]
lis.range = LIS331HHRange.RANGE_24G
range_string = LIS331HHRange.string[lis.range]
print("Range is +/-%sg" % range_string)

while True:
    print(lis.acceleration)  # plotter friendly printing
    time.sleep(0.005)
