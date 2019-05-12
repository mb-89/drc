import logging
import configparser
import os.path as op

log = logging.getLogger("drc host")
log.DEBUG = logging.DEBUG
log.INFO = logging.INFO
log._fmt = logging.Formatter('%(relativeCreated)09d | %(levelname)s | %(target)s | %(message)s')
logHandler = logging.StreamHandler()
logHandler.setFormatter(log._fmt)
log.addHandler(logHandler)
log.setLevel(log.DEBUG)
logHandler.setLevel(log.DEBUG)

from host import backend

cfg = configparser.ConfigParser()
cfg.filename = op.abspath("cfg/params")
cfg.read(cfg.filename)


be = backend.Backend(cfg)
be.run()