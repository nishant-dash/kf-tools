'''
kf pod image scanner
'''

import subprocess as sp
import os
from uuid import uuid4 as uid
import json
import yaml
from termcolor import colored
import pty


class kvs:
    def __init__(self, format, output, watch):
        self.trivy = "/snap/bin/trivy"
        self.all_info = {}
        self.color_map = {
            "critical": "red",
            "high": "red",
            "medium": "yellow",
            "low": "green",
            "unknown": "white"
        }
        self.format = format
        self.output_file = output
        self.watch = watch


    def scan(self, images):
        for i in images:
            print(f"Scanning for {i}")
            cmd = [self.trivy, "image", "--scanners", "vuln", "-f", "json", i]
            output = sp.run(cmd, stdout=sp.PIPE, stderr=sp.DEVNULL)
            if self.watch:
                cmd = [self.trivy, "image", "--scanners", "vuln", i]
                cmd = " ".join(cmd)
                sp.run(f"SYSTEMD_COLORS=1 {cmd}", shell=True)
            trivy_info = None
            try:
                trivy_info = json.loads(output.stdout)
            except json.JSONDecodeError as error:
                print(f"Trouble get json {error}, you probably hit your docker rate limit")

            # structure output
            if trivy_info:
                self.all_info[i] = []
                for result in trivy_info["Results"]:
                    for vulns in result["Vulnerabilities"]:
                        self.all_info[i].append({
                            "vulnerability_id": vulns["VulnerabilityID"],
                            "cve_primary_url": vulns["PrimaryURL"],
                            "severity": vulns["Severity"],
                        })


    def load_file(self, file):
        images_list = []
        if not os.path.exists(file):
            print(f"Can't find {file}")
            return None
        with open(file, 'r') as f:
            images_list = f.read().splitlines()
        return images_list


    def pprint(self, scan_result):
        print(f"Vulnerability ID: {scan_result['vulnerability_id']}")
        print(f"CVE Primary Url: {scan_result['cve_primary_url']}")
        sev = scan_result['severity']
        sev =  colored(sev, self.color_map[sev.lower()])
        print(f"Severity: {sev}")
        print()


    def _print(self, data):
        if not self.output_file:
            print(data)
        else:
            with open(self.output_file, 'w') as f:
                f.write(data)


    def print_report(self):
        if not self.format:
            for image, scan_results in self.all_info.items():
                print(f"Image: {image}")
                for x in scan_results:
                    self.pprint(x)
        elif self.format == "yaml":
            self._print(yaml.dump(self.all_info))
        elif self.format == "json":
            self._print(json.dumps(self.all_info))
