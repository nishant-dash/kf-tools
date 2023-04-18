import click
from kft.kf_upgrade_planner import kup
from kft.kf_image_scanner import kvs
import subprocess as sp
import os

@click.group()
@click.version_option()
def cli():
    '''
    A collection of handy wrapper tools for operators of kubeflow environments
    '''
    pass


@cli.command(
    name="logs",
    help='''
    \b
    view kf pod logs using fzf to navigate. 
    Examples:
    kft logs
    After logs, specify any quoted string to run as a bash command
    kft logs less
    kft logs view
    kft logs "less +G"
    kft logs "grep -REi 'err|fail|block|timeout'"
    ''',
)
@click.argument('args', nargs=-1)
def kpl_main(args):
    if len(args) > 1:
        print("Only accept one argument, can be quoted to provide a full bash command with flags")
    else:
        args = str(args[0]) if len(args) == 1 else ""
        executable = os.path.join(os.getcwd(), "kft/kpl.sh")
        cmd = f"{executable} {args}"
        sp.run(cmd, shell=True)
    return


epilog_check = '''
\b
To view a local bundle, extract it with
juju export-bundle -o filename
and then run,
kft check -f filename

To view bundle from the kubeflow git repo, just run with only the "-t" flag
and then a channel after it. eg: kft check -t 1.7/stable

When both local and target bundles are provided, an automatic check
for upgrade is run. eg: kft check -f localbundle -t 1.7/edge
'''
@cli.command(
    name='check',
    help='View kubeflow bundles or compare 2 bundles for possible upgrades',
    epilog=epilog_check
)
@click.option(
    "-f",
    "--file",
    help='''Input juju kubeflow bundle yaml, can specify 2 local files
        using this same flag, treating first file as src for diff
    ''',
    multiple=True,
    metavar="<file>",
)
@click.option(
    "-t",
    "--target",
    help="Target version of kubeflow bundle, ex: 1.7/stable, 1.7/beta or self",
    metavar="<target_version>",
)
@click.option(
    "--format",
    "formatting",
    help="Output format, can be yaml, json or csv",
    type=click.Choice(["yaml", "json", "csv"]),
)
@click.option(
    "-o",
    "--output",
    help="File to store output",
    metavar="<output_file>",
)
# @click.option(
#     "-g",
#     "--gen-ap",
#     "gen_ap",
#     help="generate AP for upgrades only",
#     show_default=True,
#     default=False,
#     is_flag=True,
# )
def kup_main(file, target, formatting, output):
    obj = {
        "target_version": target,
        "file": None,
        "second_file": None,
        "format": formatting,
        "output_file": output,
    }
    if file:
        if len(file) == 2 and obj["target_version"]:
            print("When checking for upgrade choose one of:")
            print("- Two local bundles,\n- One local One remote bundle")
            exit()

        obj["file"] = file[0]
        if len(file) == 2:
            obj["target_version"] = -1
            obj["second_file"] = file[1]
        elif len(file) > 2:
            print("Too many files!")
            exit()

    kupObj = kup(**obj)

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
        print(f"Inferring input bundle's version for target version as: {kupObj.target_version}")

    if kupObj.target_version == -1:
        # get second local bundle file
        target_bundle = kupObj.load_bundle(kupObj.file)
        charm_version_dict_target, kupObj.target_version = kupObj.transform(target_bundle)
    else:
        # get target bundle
        target_bundle = kupObj.download_bundle()
        if not target_bundle:
            exit()
        charm_version_dict_target, kupObj.target_version = kupObj.transform(target_bundle, get_revision=True)
    if not kupObj.file:
        kupObj.pprint(charm_version_dict_target)
        exit()

    # print upgrade opportunities
    kupObj.upgrade_flagger(source=charm_version_dict, target=charm_version_dict_target)



@cli.command(
    name="scan",
    help="Scan pod images against aquasec\'s CVE database",
    epilog="Either attemp a local scan, provide an image or a file of image names"
)
@click.option(
    "-i",
    "--image",
    help="name of a container image",
    metavar="<image_name>",
)
@click.option(
    "-f",
    "--file",
    help="file containing a list of container image names",
    metavar="<file>",
)
@click.option(
    "--format",
    "formatting",
    help="Output format, can be yaml, json or csv",
    type=click.Choice(["yaml", "json"]),
)
@click.option(
    "-o",
    "--output",
    help="File to store output",
    metavar="<output_file>",
)
@click.option(
    "-w",
    "--watch",
    help="Watch as scan results for each come in one by one",
    show_default=True,
    default=False,
    is_flag=True,
)
def kvs_main(image, file, formatting, output, watch):
    kvs_obj = kvs(formatting, output, watch)
    if image:
        kvs_obj.scan([image])
    if file:
        images_list = kvs_obj.load_file(file)
        if images_list:
            kvs_obj.scan(images_list)
    kvs_obj.print_report()


if __name__ == "__main__":
    cli()
