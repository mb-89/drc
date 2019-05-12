import configparser

class Cfg(configparser.ConfigParser):
    def __init__(self, filename):
        super().__init__(self)
        self.filename = filename
        self.read(filename)