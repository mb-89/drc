import logging

log = logging.getLogger("drc host")
log.DEBUG = logging.DEBUG
log.INFO = logging.INFO
log._fmt = logging.Formatter('%(relativeCreated)09d | %(levelname)s | %(message)s')
logHandler = logging.StreamHandler()
logHandler.setFormatter(log._fmt)
log.addHandler(logHandler)
log.setLevel(log.DEBUG)
logHandler.setLevel(log.INFO)

from host import backend

be = backend.Backend()
be.run()