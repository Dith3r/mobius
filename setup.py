#!/usr/bin/env python

from setuptools import find_namespace_packages, setup


with open("requirements.txt", "r") as file:
    requirements = file.readlines()

setup(
    name="mobius",
    version="1.0",
    packages=find_namespace_packages(
        include=["mobius", "mobius.*"], exclude=["test", "build"]
    ),
    entry_points={"console_scripts": ["mobius=mobius.app:main"]},
    install_requires=requirements,
    python_requires=">=3.10",
    zip_safe=True,
)
