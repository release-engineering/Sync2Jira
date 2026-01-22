"""
Setup configuration for the Rover_Lookup package.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [
            line.strip() for line in fh if line.strip() and not line.startswith("#")
        ]
except FileNotFoundError:
    requirements = ["ldap3>=2.9.0"]

setup(
    name="Rover_Lookup",
    version="1.0.0",
    author="sync2jira project",
    description="A Python package for translating GitHub usernames to Red Hat Associate email addresses",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
        ],
    },
)
