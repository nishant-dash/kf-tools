from setuptools import setup, find_packages 

def readf(file):
    with open(file, "r", encoding="utf-8") as f:
        return f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    reqs = f.read()

setup(
    name = 'kft',
    version = '0.1.3',
    author = 'Nishant Dash',
    author_email = 'nishant.dash@canonical.com',
    license = readf("LICENSE"),
    description = 'A collection of handy wrapper tools for operators of kubeflow environments',
    long_description = readf("README.md"),
    long_description_content_type = "text/markdown",
    url = 'https://github.com/nishant-dash/kf-tools',
    packages = find_packages(),
    install_requires = [reqs],
    python_requires='>=3.7',
    entry_points = '''
        [console_scripts]
        kft=kft.cli:cli
    '''
)
