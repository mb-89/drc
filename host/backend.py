import logging
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import os.path as op

log = logging.getLogger("drc host")

class Backend():
    def __init__(self, cfg):
        self.cfg = cfg

    def run(self):
        self.remotestartup()
        log.info("stream received, application is running", extra = {"target": "HST"})
        log.info("stopping application", extra = {"target": "HST"})
    
    def remotestartup(self):
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(AutoAddPolicy)
            ssh.connect(
                self.cfg["connection"]["bbbip"],
                username=self.cfg["connection"]["bbbuser"], 
                password=self.cfg["connection"]["bbbpw"])

            #create the destination folder if it does not exist
            log.info("updating bbb program", extra = {"target": "HST"})
            src = op.abspath(self.cfg["connection"]["bbbsrc"])
            dst = self.cfg["connection"]["bbbdst"]
            (sshin1, sshout1, ssherr1) = ssh.exec_command(f"mkdir -p {dst}")

            #copy the cfg file and the bbb code
            log.info("starting bbb program, waiting for udp stream", extra = {"target": "HST"})
            with SCPClient(ssh.get_transport()) as scp:
                scp.put(self.cfg.filename, remote_path=dst)
                scp.put(src, recursive=True, remote_path=dst)
            (sshin2, sshout2, ssherr2) = ssh.exec_command(f"python3 {dst}/bbb/__main__.py",get_pty=True)
            while not sshout2.channel.exit_status_ready():
                rawinput = sshout2.channel.recv(1024).decode("utf-8").strip()
                for x in rawinput.split("\n"):
                     if x:log.info(x, extra = {"target": "BBB"})
                #lines = sshout2.readlines()
                #for line in lines: 
            
