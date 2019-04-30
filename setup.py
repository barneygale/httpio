from setuptools import setup
from sys import version_info

packages = {
    'httpio': 'httpio'
}
install_requires = [
    'requests >= 2.10.0',
    'six'
]

if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    packages['httpio_async'] = 'httpio_async'
    install_requires.append('aiohttp >= 3.5.4')

setup(
    name='httpio',
    version='0.3.0',
    author='Barney Gale',
    author_email='barney@barneygale.co.uk',
    url='https://github.com/barneygale/httpio',
    license='MIT',
    description='HTTP resources as random-access file-like objects',
    long_description=open('README.rst').read(),
    packages=list(packages.keys()),
    package_dir=packages,
    install_requires=install_requires
)
