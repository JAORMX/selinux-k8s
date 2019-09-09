# Copyright (C) 2019 Juan Antonio Osorio Robles, <jaosorior@redhat.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import setuptools
from setuptools.command.install import install
import os

setuptools.setup(
    name="selinux-k8s",
    version="0.1.0",
    author="Juan Antonio Osorio Robles",
    author_email="jaosorior@redhat.com",
    description="A tool for generating SELinux security policies for k8s pods",
    license="GPLv3+",
    packages=["selinux_k8s"],
    entry_points={
        'console_scripts': ['selinuxk8s=selinux_k8s.selinux_k8s:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)
