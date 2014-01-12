# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='xcodeproject',
    version='0.9',
    description='Xcode project file inspection utilities',
    long_description=readme,
    author='Marc Liyanage',
    author_email='reg.python-xcodeproject@entropy.ch',
    url='https://github.com/liyanage/python-xcodeproject',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    entry_points = {
        "console_scripts": [
            "xcodeproject-util=xcodeproject.tool:XcodeprojectTool.main",
        ],
    }
)
