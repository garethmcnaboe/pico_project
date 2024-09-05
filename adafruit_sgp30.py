#library code from adafruit

import math
import time
from micropython import const

__version__ = "0.0.0-auto.0"

_SGP30_DEFAULT_I2C_ADDR  = const(0x58)
_SGP30_FEATURESET_0        = const(0x0022)
_SGP30_FEATURESET_1      = const(0x0020) 

_SGP30_CRC8_POLYNOMIAL   = const(0x31)
_SGP30_CRC8_INIT         = const(0xFF)
_SGP30_WORD_LEN          = const(2)

class Adafruit_SGP30:
    """
    A driver for the SGP30 gas sensor.
    :param i2c: The `I2C` object to use. This is the only required parameter.
    :param int address: (optional) The I2C address of the device.
    """

    def __init__(self, i2c, address=_SGP30_DEFAULT_I2C_ADDR):
        """Initialize the sensor, get the serial # and verify that we found a proper SGP30"""
        self._i2c = i2c
        self._addr = address

        self.serial = self._i2c_read_words_from_cmd([0x36, 0x82], 0.01, 3)
        featureset = self._i2c_read_words_from_cmd([0x20, 0x2f], 0.01, 1)
        if featureset[0] not in [ _SGP30_FEATURESET_0, _SGP30_FEATURESET_1 ]:
            raise RuntimeError('SGP30 Not detected')
        self.iaq_init()

    @property
    def tvoc(self):
        """Total Volatile Organic Compound in parts per billion."""
        return self.iaq_measure()[1]


    @property
    def baseline_tvoc(self):
        """Total Volatile Organic Compound baseline value"""
        return self.get_iaq_baseline()[1]

    @property
    def co2eq(self):
        """Carbon Dioxide Equivalent in parts per million"""
        return self.iaq_measure()[0]

    @property
    def baseline_co2eq(self):
        """Carbon Dioxide Equivalent baseline value"""
        return self.get_iaq_baseline()[0]

    def iaq_init(self):
        """Initialize the IAQ algorithm"""
        self._run_profile(["iaq_init", [0x20, 0x03], 0, 0.01])

    def iaq_measure(self):
        """Measure the CO2eq and TVOC"""
        return self._run_profile(["iaq_measure", [0x20, 0x08], 2, 0.05])

    def get_iaq_baseline(self):
        """Retreive the IAQ algorithm baseline for CO2eq and TVOC"""
        return self._run_profile(["iaq_get_baseline", [0x20, 0x15], 2, 0.01])

    def set_iaq_baseline(self, co2eq, tvoc):
        """Set the previously recorded IAQ algorithm baseline for CO2eq and TVOC"""
        if co2eq == 0 and tvoc == 0:
            raise RuntimeError('Invalid baseline')
        buffer = []
        for value in [tvoc, co2eq]:
            arr = [value >> 8, value & 0xFF]
            arr.append(self._generate_crc(arr))
            buffer += arr
        self._run_profile(["iaq_set_baseline", [0x20, 0x1e] + buffer, 0, 0.01])

    def set_iaq_humidity(self, gramsPM3):
        """Set the humidity in g/m3 for eCO2 and TVOC compensation algorithm"""
        tmp = int(gramsPM3 * 256)
        buffer = []
        for value in [tmp]:
            arr = [value >> 8, value & 0xFF]
            arr.append(self._generate_crc(arr))
            buffer += arr
        self._run_profile(["iaq_set_humidity", [0x20, 0x61] + buffer, 0, 0.01])

    def set_iaq_rel_humidity(self, rh, temp):
        """Set the relative humidity in % for eCO2 and TVOC compensation algorithm"""
        gramsPM3 = rh/100.0 * 6.112 * math.exp(17.62*temp/(243.12+temp))
        gramsPM3 *= 216.7 / (273.15 + temp)

        self.set_iaq_humidity(gramsPM3)

    def _run_profile(self, profile):
        """Run an SGP 'profile' which is a named command set"""
        name, command, signals, delay = profile

        return self._i2c_read_words_from_cmd(command, delay, signals)

    def _i2c_read_words_from_cmd(self, command, delay, reply_size):
        """Run an SGP command query, get a reply and CRC results if necessary"""
        self._i2c.writeto(self._addr, bytes(command))
        time.sleep(delay)
        if not reply_size:
            return None
        crc_result = bytearray(reply_size * (_SGP30_WORD_LEN +1))
        self._i2c.readfrom_into(self._addr, crc_result)
        result = []
        for i in range(reply_size):
            word = [crc_result[3*i], crc_result[3*i+1]]
            crc = crc_result[3*i+2]
            if self._generate_crc(word) != crc:
                raise RuntimeError('CRC Error')
            result.append(word[0] << 8 | word[1])
        return result

    def _generate_crc(self, data):
        """8-bit CRC algorithm for checking data"""
        crc = _SGP30_CRC8_INIT
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ _SGP30_CRC8_POLYNOMIAL
                else:
                    crc <<= 1
        return crc & 0xFF
