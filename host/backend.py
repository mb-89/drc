import logging

log = logging.getLogger("drc host")

class Backend():
    def run(self):
        log.info("connecting to bbb")
        log.info("updating bbb program")
        log.info("starting bbb program, waiting for udp stream")
        log.info("stream received, application is running")
        log.info("stopping application")