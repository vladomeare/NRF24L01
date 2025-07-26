import usys
import ustruct as struct
import utime
from machine import Pin, SPI
from nrf24l01 import NRF24L01
from micropython import const

# Slave pause between receiving data and checking for further packets.
_RX_POLL_DELAY = const(15)
# Slave pauses an additional _SLAVE_SEND_DELAY ms after receiving data and before
# transmitting to allow the (remote) master time to get into receive mode. The
# master may be a slow device. Value tested with Pyboard, ESP32 and ESP8266.
_SLAVE_SEND_DELAY = const(10)

test_led = Pin(25,Pin.OUT)
button = Pin(0, Pin.IN)

cfg = {"spi": 0, "miso": 4, "mosi": 7, "sck": 6, "csn": 14, "ce": 17}
# Addresses are in little-endian format. They correspond to big-endian
# 0xf0f0f0f0e1, 0xf0f0f0f0d2
pipes = (b"\xe1\xf0\xf0\xf0\xf0", b"\xd2\xf0\xf0\xf0\xf0")


def master():
    nrf.open_tx_pipe(pipes[0])
    nrf.open_rx_pipe(1, pipes[1])
    nrf.start_listening()

    print("NRF24L01 master mode, sending packets...")

    while True:
        # stop listening and send packet
        test_led.on()
        nrf.stop_listening()
        millis = utime.ticks_ms()
        val = button.value()
        print("sending:", millis, val)
        try:
            nrf.send(struct.pack("ii", millis, val))
        except OSError:
            pass

        # start listening again
        nrf.start_listening()

        # wait for response, with 250ms timeout
        start_time = utime.ticks_ms()
        timeout = False
        while not nrf.any() and not timeout:
            if utime.ticks_diff(utime.ticks_ms(), start_time) > 250:
                timeout = True

        if timeout:
            print("failed, response timed out")

        else:
            # recv packet
            (got_millis,) = struct.unpack("i", nrf.recv())

            # print response and round-trip delay
            print(
                "got response:",
                got_millis,
                "(delay",
                utime.ticks_diff(utime.ticks_ms(), got_millis),
                "ms)",
            )
        test_led.off()
        # delay then loop
        utime.sleep_ms(250)

    print("master finished sending; successes=%d, failures=%d" % (num_successes, num_failures))


def slave():
    nrf.open_tx_pipe(pipes[1])
    nrf.open_rx_pipe(1, pipes[0])
    nrf.start_listening()

    print("NRF24L01 slave mode, waiting for packets... (ctrl-C to stop)")

    while True:
        if nrf.any():
            while nrf.any():
                buf = nrf.recv()
                millis, val = struct.unpack("ii", buf)
                print("received:", millis, val)
                if val == 1:
                    test_led.on()
                else:
                    test_led.off()
                utime.sleep_ms(_RX_POLL_DELAY)

            # Give master time to get into receive mode.
            utime.sleep_ms(_SLAVE_SEND_DELAY)
            nrf.stop_listening()
            millis = utime.ticks_ms()
            try:
                nrf.send(struct.pack("i", millis))
            except OSError:
                pass
            print("sent response")
            nrf.start_listening()


print("NRF24L01 test module loaded")
print("NRF24L01 pinout for test:")
print("    SPI on", cfg["spi"])
print("    CE on", cfg["ce"])
print("    CSN on", cfg["csn"])
print("    SCK on", cfg["sck"])
print("    MISO on", cfg["miso"])
print("    MOSI on", cfg["mosi"])
print("run nrf24l01test.slave() on slave, then nrf24l01test.master() on master")

csn = Pin(cfg["csn"], mode=Pin.OUT, value=1)
ce = Pin(cfg["ce"], mode=Pin.OUT, value=0)
spi = SPI(cfg["spi"], sck=Pin(cfg["sck"]), mosi=Pin(cfg["mosi"]), miso=Pin(cfg["miso"]))
nrf = NRF24L01(spi, csn, ce, payload_size=8)
