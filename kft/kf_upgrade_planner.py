'''
Tool to parse current deployment bundle, extrapolate possible kubeflow version and 
print rudimentary upgrade path/steps
'''

import yaml
from tabulate import tabulate as tab
import requests
import subprocess as sp
import os
from uuid import uuid4 as uid
from textwrap import dedent
from tqdm import tqdm
from termcolor import colored
import json
import csv
import sys


class kup:
    def __init__(self, **kwargs):
        self.kf_source = "https://github.com/canonical/bundle-kubeflow"
        self.upgrade_docs = f"{self.kf_source}/tree/main/docs"
        self.anchor_app = "kubeflow-dashboard"
        self.index = {"beta": 0, "stable": 1, "edge": 2}
        self.juju = "juju"
        self.output_formats = ["yaml", "json", "csv"]
        for k,v in kwargs.items():
            setattr(self, k, v)


    def _print(self, output, csv_flag=False):
        if not self.output_file:
            if csv_flag:
                writer = csv.writer(sys.stdout)
                writer.writerows(output)
            else:
                print(output)
        else:
            # check validity of file
            if '/' in self.output_file:
                path = self.output_file.split('/')
                path = "/".join(path[:-1])
                if not os.path.exists(self.output_file):
                    print(f"Invalid path {path}")
                    return
            with open(self.output_file, 'w') as f:
                if csv_flag:
                    writer = csv.writer(f)
                    writer.writerows(output)
                else:
                    f.write(output)


    # Styled print with optional upgrade markers
    # Supports table, yaml, json and csv 
    def pprint(self, d, upgrades=False):
        if self.format == "yaml":
            self._print(yaml.dump(d))
        elif self.format == "json":
            self._print(json.dumps(d))
        else:
            temp = []
            if upgrades:
                fields = ["Charm", "Src Channel", "S", "Dst Channel", "Src Rev", "S", "Dst Rev"]
                for k,v in d.items():
                    temp.append([k] + [v2 for v2 in v.values()])
                    if not self.output_file:
                        if '->' in temp[-1]:
                            temp[-1] = [colored(str(i), 'green') if i else i for i in temp[-1]]
            else:
                fields = ["Charm", "Channel", "Revision"]
                for k,v in d.items():
                    temp2 = [k]
                    for k2, v2 in v.items():
                        if k2 != "charm_name":
                            temp2.extend([v2])
                    temp.append(temp2)
            if self.format == "csv":   
                self._print([fields] + temp, csv_flag=True)
            else:
                self._print(tab(temp, headers=fields))


    # Transform the juju bundle yaml to a dict that maps
    # charm name -> {channel, revision}
    def transform(self, bundle, get_revision=False):
        charm_version_dict = {}
        if not get_revision:
            for charm, info in bundle["applications"].items():
                rev = "Not found"
                if "revision" in info:
                    rev = info["revision"]
                charm_version_dict[charm] = {"channel": info["channel"], "revision": rev}
        else:
            for charm, info in bundle["applications"].items():
                charm_version_dict[charm] = {"channel": info["channel"], "charm_name": info["charm"]}
            self.get_reversion_numbers(charm_version_dict)

        return charm_version_dict , charm_version_dict[self.anchor_app]["channel"]


    # hacky function to check downgrade
    def check_downgrade(self, source, target):
        src = source[self.anchor_app]
        dst = target[self.anchor_app]
        src_channel, src_mode = src["channel"].split("/")
        dst_channel, dst_mode = dst["channel"].split("/")

        # if dst_channel == "latest":
        #     if src_channel == "latest":
        #         if self.index[dst_mode] < self.index[src_mode]:
        #             print("Downgrade detected!")
        #             return True
        if float(dst_channel) < float(src_channel):
            print("Downgrade detected!")
            return True
        elif dst_channel == src_channel:
            if self.index[dst_mode] < self.index[src_mode]:
                print("Downgrade detected!")
                return True
        elif int(dst["revision"]) < int(src["revision"]):
            print("Downgrade detected!")
            return True
        return False



    # print a diff of the bundle in a manner that flags apps for upgrades
    def upgrade_flagger(self, source, target):
        final_dict = {}
        num_changes = 0

        final_view = {}
        for charm, info in target.items():
            final_view[charm] = {"src": None, "dst": None}
            final_view[charm]["dst"] = info
            if charm in source:
                if charm not in final_view:
                    final_view[charm] = {"src": None, "dsr": None}
                final_view[charm]["src"] = source[charm]

        for charm, view in final_view.items():
            final_dict[charm] = {
                "src_channel": None, "channel_upgrade" : None,"dst_channel": None,
                "src_revision": None, "revision_upgrade" : None, "dst_revision": None,
            }
            if view["src"]: 
                final_dict[charm]["src_channel"] = view["src"]["channel"]
                final_dict[charm]["src_revision"] = int(view["src"]["revision"])
            if view["dst"]: 
                final_dict[charm]["dst_channel"] = view["dst"]["channel"]
                final_dict[charm]["dst_revision"] = int(view["dst"]["revision"])
            
            if final_dict[charm]["src_channel"] and final_dict[charm]["dst_channel"]:
                if final_dict[charm]["dst_channel"] != final_dict[charm]["src_channel"]:
                    final_dict[charm]["channel_upgrade"] = "->"
            if final_dict[charm]["src_revision"] and final_dict[charm]["dst_revision"]:
                if final_dict[charm]["dst_revision"] > final_dict[charm]["src_revision"]:
                    final_dict[charm]["revision_upgrade"] = "->"

            if final_dict[charm]["channel_upgrade"] or final_dict[charm]["revision_upgrade"]:
                num_changes += 1
            if not final_dict[charm]["src_channel"] and final_dict[charm]["dst_channel"]:
                final_dict[charm]["channel_upgrade"] = "+"
                final_dict[charm]["revision_upgrade"] = "+"

        self.pprint(final_dict, upgrades=True)
        print(f"\n{num_changes} charms need upgrades!")

        apps_to_remove = []
        for app in source.keys():
            if app not in target:
                apps_to_remove.append(app)
        if len(apps_to_remove) > 0:
            print(f"{len(apps_to_remove)} charms not found in target bundle: {apps_to_remove}")

        self.check_downgrade(source, target)
        print(f"Also check upgrade docs at {self.upgrade_docs} for any relevant steps and caveats!")


    # function to query charmhub with juju to get version numbers for apps
    def get_reversion_numbers(self, bundle):
        # before we can return target bundle, we need to get revision numbers from
        # charmhub. Currently, the kf bundle in the git repo does not include such
        # information.
        print("Getting revision numbers from charmhub via local juju tool...")
        # for each charm, check with juju info to see what revision you get
        for charm, info in tqdm(bundle.items()):
            # get the juju info as yaml
            cmd = [self.juju, "info", info["charm_name"], "--format", "json"]
            output = sp.run(cmd, stdout=sp.PIPE, stderr=sp.DEVNULL)
            # parse yaml for what we need
            juju_info = ""
            try:
                juju_info = json.loads(output.stdout)
            except json.JSONDecodeError as error:
                print(error)
            channels = juju_info["channel-map"]
            if info["channel"] not in channels:
                bundle[charm]["revision"] = "Error"
            else:    
                bundle[charm]["revision"] = channels[info["channel"]]["revision"]

    # load target kubeflow bundle from github for comparison
    def download_bundle(self):
        if not self.target_version:
            print("Unable to get target version")
            return
        target_bundle = None
        version, channel = self.target_version.split("/")
        url = f"{self.kf_source}/raw/main/releases/{version}/{channel}/kubeflow/bundle.yaml"
        response = requests.get(url)
        print (f"Downloading kf {self.target_version} bundle...")
        if response.status_code != 200:
            response.raise_for_status()
            print(f"Target bundle for Kubeflow {self.target_version} not found!")
        else:
            try:
                target_bundle = yaml.safe_load(response.content)
            except yaml.YAMLError as error:
                print(error)

        return target_bundle


    # Yaml safe load juju bundle
    def load_bundle(self, bundle_file):
        bundle = None
        with open(bundle_file, "r") as f:
            try:
                bundle = yaml.safe_load(f)
            except yaml.YAMLError as error:
                print(error)
        return bundle
