from distutils.core import setup
from setuptools import find_namespace_packages

setup(
    name='cosmic17-wire',
    version='0.1',
    description='',
    long_description=open('README.md').read(),
    packages=find_namespace_packages(where='src'),
    package_dir={'': 'src'},
    license='GPLv2',
    url='https://github.com/RandomRedBeard/cosmic17-wire',
    author='Thomas Jansen',
    author_email='tnj@17cosmicln.net'
)