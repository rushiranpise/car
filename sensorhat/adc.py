#!/usr/bin/env python3
from .i2c import I2C


class ADC(I2C):
    """
    Analog to digital converter
    """
    ADDR = [0x14, 0x15]

    def __init__(self, chn, address=None, *args, **kwargs):
        """
        Analog to digital converter

        :param chn: channel number (0-7/A0-A7)
        :type chn: int/str
        """
        if address is not None:
            super().__init__(address, *args, **kwargs)
        else:
            super().__init__(self.ADDR, *args, **kwargs)
        self._debug(f'ADC device address: 0x{self.address:02X}')

        if isinstance(chn, str):
            if chn.startswith("A"):
                chn = int(chn[1:])
            else:
                raise ValueError(
                    f'ADC channel should be between [A0, A7], not "{chn}"')
        if chn < 0 or chn > 7:
            raise ValueError(
                f'ADC channel should be between [0, 7], not "{chn}"')
        chn = 7 - chn
        self.chn = chn | 0x10

    def read(self):
        """
        Read the ADC value

        :return: ADC value(0-4095)
        :rtype: int
        """
        self.write([self.chn, 0, 0])
        msb, lsb = super().read(2)

        value = (msb << 8) + lsb
        self._debug(f"Read value: {value}")
        return value

    def read_voltage(self):
        """
        Read the ADC value and convert to voltage

        :return: Voltage value(0-3.3(V))
        :rtype: float
        """
        value = self.read()
        voltage = value * 3.3 / 4095
        self._debug(f"Read voltage: {voltage}")
        return voltage
