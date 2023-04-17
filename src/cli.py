import click

@click.group()
def cli():
    pass


@cli.command(name='check', help='View kubeflow bundles and compare 2 bundles for possible upgrades')
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
def kup(file, target, output):
    print(f"{file} {target} {output}")
    return


if __name__ == "__main__":
    cli()