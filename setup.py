from setuptools import setup

setup(
    name='httpio',
    version='0.1.4',
    author='Barney Gale',
    author_email='barney@barneygale.co.uk',
    url='https://github.com/barneygale/httpio',
    license='MIT',
    description='HTTP resources as random-access file-like objects',
    long_description=open('README.rst').read(),
    py_modules=['httpio'],
    install_requires=['requests >= 2.10.0'],
)
