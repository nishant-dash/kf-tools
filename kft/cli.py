import click
from kup import kup as kup


@click.group()
def cli():
    '''
    A collection of handy tools for operators of kubeflow environments
    '''
    pass


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
            print("Two local bundles, 1 local 1 remote bundle")
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


if __name__ == "__main__":
    cli()