#!/usr/bin/bash

if [ -n "$rcm_tools_repos" ]; then
    repo_file=/etc/yum.repos.d/rcm-tools-fedora.repo
    curl -L -o $repo_file $rcm_tools_repos
    # Since we don't trust any internal CAs at this point, we must connect over
    # http
    sed -i 's/https:/http:/g' $repo_file

    dependencies=(python3-rhmsg)

    dnf install -y \
    --setopt=deltarpm=0 \
    --setopt=install_weak_deps=false \
    --setopt=tsflags=nodocs \
    ${dependencies[@]}

    dnf clean all
fi
