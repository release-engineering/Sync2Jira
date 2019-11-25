#!/bin/bash
set -e
# SPDX-License-Identifier: GPL-2.0+

# Generate a version number from the current code base.

name=sync2jira
if [ "$(git tag | wc -l)" -eq 0 ] ; then
    # never been tagged since the project is just starting out
    lastversion="0.0"
    revbase=""
else
    lasttag="$(git describe --abbrev=0 HEAD)"
    lastversion="${lasttag##${name}-}"
    revbase="^$lasttag"
fi
if [ "$(git rev-list $revbase HEAD | wc -l)" -eq 0 ] ; then
    # building a tag
    rpmver=""
    rpmrel=""
    version="$lastversion"
else
    # git builds count as a pre-release of the next version
    version="$lastversion"
    version="${version%%[a-z]*}" # strip non-numeric suffixes like "rc1"
    # increment the last portion of the version
    version="${version%.*}.$((${version##*.} + 1))"
    commitcount=$(git rev-list $revbase HEAD | wc -l)
    commitsha=$(git rev-parse --short HEAD)
    rpmver="${version}"
    rpmrel="0.git.${commitcount}.${commitsha}"
    version="${version}.dev${commitcount}+git.${commitsha}"
fi

export SYNC2JIRA_VERSION=$version
export SYNC2JIRA_RPM_VERSION=$rpmver
export SYNC2JIRA_RPM_RELEASE=$rpmrel
export SYNC2JIRA_CONTAINER_VERSION=${version/+/-}
