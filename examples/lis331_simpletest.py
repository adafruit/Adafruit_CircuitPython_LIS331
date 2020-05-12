import time
import board
import busio
import adafruit_lis331
from adafruit_debug_i2c import DebugI2C

i2c = busio.I2C(board.SCL, board.SDA)
i2c = DebugI2C(i2c)
lis = adafruit_lis331.LIS331(i2c)

for i in range(2):
    print("Acceleration : X: %.2f, Y:%.2f, Z:%.2f ms^2" % lis.acceleration)
    time.sleep(0.1)
