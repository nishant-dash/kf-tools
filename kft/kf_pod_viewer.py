import subprocess as sp


class kpv:
    def __init__(self)
        self.kubectl = "kubectl"
        self.namespace = "kubeflow"
        self.logs = True
        self.describe = False
        self.ssh = False
        self.preview = True
        return

    def build_cmd(self):
        ns = ""
        if self.namespace == -1:
            ns = ["--all-namespaces"]
        else:
            ns = f"-n {self.namespace}"
        mode = ""
        extra_mode = ""
        if self.logs:
            mode = "logs"
            extra_mode = "--tail=100"
        elif self.describe:
            mode = "describe"
        elif self.ssh:
            mode = "exec pod"
            extra_mode = "-- bash"

        cmd = f"{self.kubectl} {ns} {mode} {extra_mode}"
        
