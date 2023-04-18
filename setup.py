from setuptools import setup, find_packages 

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()

setup(
    name = 'kft',
    version = '0.1',
    author = 'Nishant Dash',
    author_email = 'nishant.dash@canonical.com',
    license = 'MIT',
    description = 'A collection of handy tools for operators of kubeflow environments',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/nishant-dash/kf-tools',
    py_modules = ['kft'],
    packages = find_packages(),
    install_requires = [requirements],
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Kubeflow Operator Tools :: Pyhton"
    ],
    entry_points = '''
        [console_scripts]
        kft=kft.cli:cli
    '''
)
