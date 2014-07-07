DGRAM_DELIMITER = "^"

class ServerPacket(object):
    def __init__(self, values = None):
        if values:
            self.values = self.read_values(values)
        else:
            self.values = []

    def add_int(self, intval):
        self.values.append(intval)

    def get_int(self):
        val = self.values.pop(0)
        return int(val)

    def add_float(self, floatval):
        self.values.append(floatval)

    def get_float(self):
        val = self.values.pop(0)
        return float(val)

    def add_string(self, stringval):
        self.values.append(stringval)

    def get_string(self):
        return self.values.pop(0)

    def add_bool(self, boolval):
        self.values.append(int(boolval))

    def get_bool(self):
        val = self.values.pop(0)
        return bool(int(val))

    def read_values(self, datagram):
        return datagram.split(DGRAM_DELIMITER)

    def get_datagram(self):
        return reduce(lambda x,y: str(x)+DGRAM_DELIMITER+str(y), self.values)