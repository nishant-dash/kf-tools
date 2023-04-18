
# kf-tools
### A collection of handy wrapper tools for operators of kubeflow environments


With kf-tools you have access to a few command line tools to help you operate your kubeflow deployment. These include:


1) kft logs (Kube Pod Logs viewer)
A [fuzzy finder](https://github.com/junegunn/fzf) based utility for navigating pods, and then viewing them with CLI tools such as less, view, or any viewing tool. You can just apply any command after kpl such as grep, etc...

2) kft check (Kube Upgrade Planner)
A tool to help you view your juju based kubeflow bundle, in terms of the charm, channel and revision. You can compare 2 local bundles or compare a local with a remote charmed kubeflow bundle and view the differences between these bundles based off their versioning information.

3) kft scan (Kube Vulnerability Scanner)
This scanner uses [trivy](https://github.com/aquasecurity/trivy) to help you scan your pod images against a databases of known vulnerabilities. It does not scan the container image itself, but for references of CVEs against the image.


## Installation

### Install from source

```bash
git clone git@github.com:nishant-dash/kf-tools.git
cd kf-tools/ && python3 setup.py install
./install.sh
```

### Install from pip
**Note, since these are wrapper scripts they use commands like juju, kubectl, fzf and trivy
all of these are in install.sh (except juju and kubectl)**

```bash
pip install kft
```

### Install from snap (WIP)

```bash
sudo snap install kft
```

## Usage

You can view all subcommands and flags with `-h` or `--help`.

### kft logs (Kube Pod Logs viewer)

```bash
# use it as is
kft logs

# use it with less (default) or view
kft logs less
kft logs view

# give it some extra flags
kft logs "less +G"

# grep the logs for anything you need
kft logs "grep -iE 'error|block|fail|lost|timeout'"
```


### kft check (Kube Upgrade Planner)

```bash
# run against local environment, this will run juju commands
kft check -l

# view a local bundle
kft check -f my-kf-bundle.yaml

# view a remote bundle
kft check -t 1.7/stable

# compare a local and remote bundle
kft check -f my-kf-bundle.yaml -t 1.7/stable

# compare two local bundles
kft check -f my-kf-bundle.yaml -f my-kf-bundle2.yaml

# compare two local bundles and get a yaml/json output
kft check -f my-kf-bundle.yaml -f my-kf-bundle2.yaml --format yaml -o output.yaml
```

### kft scan (Kube Vulnerability Scanner)

```bash
# scan a particular container image
kft scan -i <image_name>

# scan a files of image names 
kft scan -f <file>

# generate a yaml/json report
kft scan -f <file> --format json

# watch output as it scans
kft scan -f <file> -w

# Not Out yet
# scan current local kubeflow installation that your juju controller has access to 
# and your kubectl command line tool is configured with
# this command is namespaced, with the default of kubeflow
kft scan

# scan other namespace(s) or all namespaces (default is kubeflow)
kft scan -n monitoring -s
kft scan -n monitoring,custom,kubeflow -s
kft scan --all-namespaces
```
