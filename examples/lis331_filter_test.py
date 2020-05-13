import time
import board
import busio
from adafruit_lis331 import LIS331, Rate, Frequency, LIS331HHRange

i2c = busio.I2C(board.SCL, board.SDA)
lis = LIS331HH(i2c)

lis.data_rate = Rate.RATE_LOWPOWER_10_HZ
print("Rate is %sHz" % Rate.string[lis.data_rate])

lis.lpf_cutoff = Frequency.FREQ_37_HZ
print("LPF cutoff frequency is %sHz" % Frequency.string[lis.lpf_cutoff])

lis.range = LIS331HHRange.RANGE_24G
print("Range is +/-%sg" % LIS331HHRange.string[lis.range])

while True:
    print(lis.acceleration)  # plotter friendly printing
    time.sleep(0.005)
