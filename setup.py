from setuptools import setup

# Basic metadata
name = 'httpio_bbc'
description = 'HTTP resources as random-access file-like objects'
url = 'https://github.com/bbc/httpio'
author = 'Barney Gale, now maintained by BBC R&D'
author_email = 'cloudfit-opensource@rd.bbc.co.uk'
license = 'MIT'

try:
    long_description = open('README.rst').read()
except FileNotFoundError:
    # Readme file not available yet, just use the short description for now
    long_description = description

# Execute version file to set version variable
try:
    with open(("{}/_version.py".format(name)), "r") as fp:
        exec(fp.read())
except IOError:
    # Version file doesn't exist, fake it for now
    __version__ = "0.0.0"

package_names = [
    'httpio_bbc',
]
packages = {
    pkg: pkg.replace('.', '/') for pkg in package_names
}

packages_required = [
    "requests >= 2.10.0",
    "six",
    "aiohttp >= 3.5.4",
]

setup(
    name=name,
    python_requires='>=3.10',
    version=__version__,
    description=description,
    url=url,
    author=author,
    author_email=author_email,
    license=license,
    packages=package_names,
    package_dir=packages,
    package_data={
    },
    install_requires=packages_required,
    scripts=[],
    data_files=[],
    long_description=long_description
)
