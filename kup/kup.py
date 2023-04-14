'''
Tool to parse current deployment bundle, extrapolate possible kubeflow version and 
print rudimentary upgrade path/steps
'''

import yaml
import argparse
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
    def __init__(self):
        self.kf_source = "https://github.com/canonical/bundle-kubeflow"
        self.upgrade_docs = f"{self.kf_source}/tree/main/docs"
        self.anchor_app = "kubeflow-dashboard"
        self.index = {"beta": 0, "stable": 1, "edge": 2}
        self.juju = "/snap/bin/juju"
        self.output_formats = ["yaml", "json", "csv"]
        self.file = None
        self.target_version = None
        self.format = None
        self.output_file = None
        self.second_file = None


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
        if not os.path.exists(self.juju):
            print("Can't find juju snap! Need that to query charmhub")
            return None

        print("Getting revision numbers from charmhub via local juju tool...")
        # for each charm, check with juju info to see what revision you get
        for charm, info in tqdm(bundle.items()):
            # temp file for the bundle
            temp_file = f"/tmp/temp-{charm}-info-{uid()}.yaml"
            # get the juju info as yaml
            cmd = [self.juju, "info", info["charm_name"], "--format", "yaml", "-o", temp_file]
            sp.run(cmd, stderr=sp.DEVNULL)
            # print(" ". join(cmd))
            # parse yaml for what we need
            juju_info = ""
            with open(temp_file, "r") as f:
                try:
                    juju_info = yaml.safe_load(f)
                except yaml.YAMLError as error:
                    print(error)
            # print(charm)
            # print(bundle[charm])
            # print(juju_info["channel-map"].keys())
            channels = juju_info["channel-map"]
            if info["channel"] not in channels:
                bundle[charm]["revision"] = "Error"
            else:    
                bundle[charm]["revision"] = channels[info["channel"]]["revision"]
            # print(bundle[charm])
            # remove temp file
            cmd = ["rm", temp_file]
            sp.run(cmd)

    # load target kubeflow bundle from github for comparison
    def download_bundle(self, target_version):
        target_bundle = None
        version, channel = target_version.split("/")
        url = f"{self.kf_source}/raw/main/releases/{version}/{channel}/kubeflow/bundle.yaml"
        response = requests.get(url)
        print ("Downloading bundle...")
        if response.status_code != 200:
            response.raise_for_status()
            print(f"Target bundle for Kubeflow {target_version} not found!")
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


    # Initialize and load script arguments
    def load_args(self):
        parser = argparse.ArgumentParser(
            # epilog="Tool to view kubeflow bundles and compare 2 bundles for possible upgrades"
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=dedent('''\
            Additional information:
                To view a local bundle, you can extract it with
                "juju export-bundle > filename" and then pass it to the tool as:
                kup -s filename

                To view bundle from the git repo, just run with only the "-t" flag
                and then a channel after it.
                
                When both local and target bundles are provided, an automatic check
                for upgrade is run.
            ''')
        )
        parser.add_argument(
            "-f",
            "--file",
            help=dedent('''\
                Input juju kubeflow bundle yaml, can specify 2 local files
                using this same flag, treating first file as src for diff
            '''),
            action="append",
            nargs='+',
        )
        parser.add_argument(
            "-t",
            "--target",
            help="Target version of kubeflow bundle, ex: 1.7/stable, 1.7/beta or self",
        )
        parser.add_argument(
            "--format",
            help="Output format, can be yaml, json or csv",
            choices=self.output_formats,
            type=str.lower,
        )
        parser.add_argument(
            "-o",
            "--output",
            help="File to store output",
        )
        # @TODO
        # add arg for generating action plans
        # and clean up output formatting
        # create args
        args = parser.parse_args()
        self.target_version = args.target
        if len(args.file) == 2 and self.target_version:
            print("When checking for upgrade choose one of:")
            print("Two local bundles, 1 local 1 remote bundle")
            exit()
        if args.file:
            self.file = args.file[0][0]
            if len(args.file) == 2:
                self.target_version = -1
                self.second_file = args.file[1][0]
            elif len(args.file) > 2:
                print("Too many files!")
                exit()
        self.format = args.format
        self.output_file = args.output


if __name__ == '__main__':
    # instantiate kup object
    kupObj = kup()

    # get args
    kupObj.load_args()
    local_version = None
    if kupObj.file:
        # get local bundle
        local_bundle = kupObj.load_bundle(kupObj.file)
        charm_version_dict, local_version = kupObj.transform(local_bundle)
        if not kupObj.target_version:
            kupObj.pprint(charm_version_dict)
            exit()

    if kupObj.target_version == "self":
        kupObj.target_version = local_version
        print(f"Inferring local version for target version as: {kupObj.target_version}")

    if not kupObj.target_version:
        print("Unable to get target version")
        exit()
    
    if kupObj.target_version == -1:
        # get second local bundle file
        target_bundle = kupObj.load_bundle(kupObj.file)
        charm_version_dict_target, kupObj.target_version = kupObj.transform(target_bundle)
    else:
        # get target bundle
        target_bundle = kupObj.download_bundle(kupObj.target_version)
        if not target_bundle:
            exit()
        charm_version_dict_target, kupObj.target_version = kupObj.transform(target_bundle, get_revision=True)
    if not kupObj.file:
        kupObj.pprint(charm_version_dict_target)
        exit()

    # print upgrade opportunities
    kupObj.upgrade_flagger(source=charm_version_dict, target=charm_version_dict_target)
