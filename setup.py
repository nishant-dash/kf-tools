from setuptools import setup, find_packages 

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read()

with open("LICENSE", "r", encoding="utf-8") as f:
    kft_license = f.read()

setup(
    name = 'kft',
    version = '0.1',
    author = 'Nishant Dash',
    author_email = 'nishant.dash@canonical.com',
    license = kft_license,
    description = 'A collection of handy wrapper tools for operators of kubeflow environments',
    long_description = readme,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/nishant-dash/kf-tools',
    py_modules = ['kft'],
    packages = find_packages(),
    install_requires = [requirements],
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3.8",
    ],
    entry_points = '''
        [console_scripts]
        kft=kft.cli:cli
    '''
)
