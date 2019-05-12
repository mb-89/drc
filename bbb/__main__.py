import logging
import os.path as op
import time

log = logging.getLogger("drc bbb")
log.DEBUG = logging.DEBUG
log.INFO = logging.INFO
log._fmtfull = logging.Formatter('%(relativeCreated)09d | %(levelname)s | %(message)s')
log._fmtred  = logging.Formatter('%(message)s')

logHandler = logging.StreamHandler()
logHandler.setFormatter(log._fmtred)
log.addHandler(logHandler)
logHandler.setLevel(log.DEBUG)

filehandler = logging.FileHandler(op.dirname(op.realpath(__file__))+"/log","w+")
filehandler.setFormatter(log._fmtfull)
log.addHandler(filehandler)
filehandler.setLevel(log.DEBUG)

log.setLevel(log.DEBUG)

log.info("started bbb code")
time.sleep(2)
log.info("done")