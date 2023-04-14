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
import time
from tqdm import tqdm
from termcolor import colored


class kup:
    def __init__(self):
        self.kf_source = "https://github.com/canonical/bundle-kubeflow"
        self.upgrade_docs = f"{self.kf_source}/tree/main/docs"
        return

    # Table style print
    def pprint(self, d):
        temp = []
        for k,v in d.items():
            temp2 = [k]
            for k2, v2 in v.items():
                if k2 != "charm_name":
                    temp2.extend([v2])
            temp.append(temp2)
        print(tab(temp, headers=["Charm", "Channel", "Revision"]))


    # Table style print with upgrade markers
    def pprint_upgrades(self, d):
        temp = []
        for k,v in d.items():
            temp.append([k] + [v2 for v2 in v.values()])
            if '->' in temp[-1]:
                temp[-1] = [colored(str(i), 'green') if i else i for i in temp[-1]]
        print(tab(temp, headers=["Charm", "Src Channel", "S", "Dst Channel", "Src Rev", "S", "Dst Rev"]))


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

        return charm_version_dict , charm_version_dict["kubeflow-dashboard"]["channel"]


    # hacky function to check downgrade
    def check_downgrade(self, source, target):
        index = {"beta": 0, "stable": 1, "edge": 2,}
        anchor_app = "kubeflow-dashboard"
        src = source[anchor_app]
        dst = target[anchor_app]
        src_channel, src_mode = src["channel"].split("/")
        dst_channel, dst_mode = dst["channel"].split("/")

        # if dst_channel == "latest":
        #     if src_channel == "latest":
        #         if index[dst_mode] < index[src_mode]:
        #             print("Downgrade detected!")
        #             return True
        if float(dst_channel) < float(src_channel):
            print("Downgrade detected!")
            return True
        elif dst_channel == src_channel:
            if index[dst_mode] < index[src_mode]:
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

        self.pprint_upgrades(final_dict)
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
        if not os.path.exists("/snap/bin/juju"):
            print("Can't find juju snap! Need that to query charmhub")
            return None

        print("Getting revision numbers from charmhub via local juju tool...")
        # for each charm, check with juju info to see what revision you get
        for charm, info in tqdm(bundle.items()):
            # temp file for the bundle
            temp_file = f"/tmp/temp-{charm}-info-{uid()}.yaml"
            # get the juju info as yaml
            cmd = ["/snap/bin/juju", "info", info["charm_name"], "--format", "yaml", "-o", temp_file]
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
def arg_loader():
    parser = argparse.ArgumentParser(
        # epilog="Tool to view kubeflow bundles and compare 2 bundles for possible upgrades"
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent('''\
        Additional information:
            To view a local bundle, you can extract it with
            "juju export-bundle > filename" and then pass it to the tool as:
            kubeflow-upgrade-planner -s filename

            To view bundle from the git repo, just run with only the "-t" flag
            and then a channel after it.
            
            When both local and target bundles are provided, an automatic check
            for upgrade is run.
        ''')
    )
    parser.add_argument("-f", "--file", help="Input juju kubeflow bundle yaml")
    parser.add_argument(
        "-t",
        "--target",
        help="Target version of kubeflow bundle, ex: 1.7/stable, 1.7/beta or 1.7/edge"
    )
    # create args
    args = parser.parse_args()
    return args.file, args.target



if __name__ == '__main__':
    # get args
    file, target_version = arg_loader()

    # instantiate kup object
    kupObj = kup()
    local_version = None
    if file:
        # get local bundle
        local_bundle = kupObj.load_bundle(file)
        charm_version_dict, local_version = kupObj.transform(local_bundle)
        if not target_version:
            kupObj.pprint(charm_version_dict)
            exit()

    if target_version == "self":
        target_version = local_version
        print(f"Inferring local version for target version as: {target_version}")

    if not target_version:
        print("Unable to get target version")
        exit()
    # get target bundle
    target_bundle = kupObj.download_bundle(target_version)
    if not target_bundle:
        exit()
    charm_version_dict_target, target_version = kupObj.transform(target_bundle, get_revision=True)
    if not file:
        kupObj.pprint(charm_version_dict_target)
        exit()

    # print upgrade opportunities
    kupObj.upgrade_flagger(source=charm_version_dict, target=charm_version_dict_target)
