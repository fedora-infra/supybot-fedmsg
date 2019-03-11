#!/usr/bin/env python

import sys
from setuptools import setup

f = open('README.rst')
long_description = f.read().strip()
f.close()

setup(
    name='supybot-fedmsg',
    version='0.2.0',
    description="Supybot plugin for emitting events to the Fedora message bus",
    long_description=long_description,
    author='Ralph Bean',
    author_email='rbean@redhat.com',
    url='http://github.com/ralphbean/supybot-fedmsg/',
    license='LGPLv2+',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=['supybot-fedmsg'],
    include_package_data=True,
    zip_safe=False,
)
