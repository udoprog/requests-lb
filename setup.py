#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import requests_lb

NAME = "requests-lb"
VERSION = str(requests_lb.VERSION)

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name=NAME,
    version=VERSION,
    description="A load-balancing wrapper around requests",
    author=["John-John Tedro"],
    author_email=["udoprog@tedro.se"],
    license="Apache 2.0",
    packages=["requests_lb"],
    scripts=["bin/lbcurl"],
    install_requires=required,
    test_suite = 'nose.collector',
)
