# This file is part of sync2jira.
# Copyright (C) 2016 Red Hat, Inc.
#
# sync2jira is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# sync2jira is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with sync2jira; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110.15.0 USA
#
# Authors:  Ralph Bean <rbean@redhat.com>
from setuptools import setup
import os

with open('requirements.txt', 'rb') as f:
    install_requires = f.read().decode('utf-8').split('\n')
    if not os.getenv('READTHEDOCS'):
        install_requires.append('requests-kerberos')

with open('test-requirements.txt', 'rb') as f:
    test_requires = f.read().decode('utf-8').split('\n')

setup(
    name='sync2jira',
    version=2.0,
    description="Sync pagure and github issues to jira, via fedmsg",
    author='Ralph Bean',
    author_email='rbean@redhat.com',
    url='https://pagure.io/sync-to-jira',
    license='LGPLv2+',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU Lesser General "
        "Public License v2 or later (LGPLv2+)",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
    ],
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='nose.collector',
    packages=[
        'sync2jira',
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            "sync2jira=sync2jira.main:main",
            "sync2jira-list-managed-urls=sync2jira.main:list_managed",
            "sync2jira-close-duplicates=sync2jira.main:close_duplicates",
        ],
    },
)
