import os.path as op

from host import logger
from host import cfg
from host import frontend
from host import backend

be = backend.Backend(cfg.Cfg("cfg/params"))
fe = frontend.Frontend(be)

fe.run()