#!/usr/bin/bash

main() {
  if [ -n "$RCM_TOOLS_REPO" ]; then
      repo_file=/usr/local/src/sync2jira/continuous-deployment/rcm-tools-fedora.repo
      curl -L -o $repo_file $RCM_TOOLS_REPO
      # Since we don't trust any internal CAs at this point, we must connect over
      # http
      sed -i 's/https:/http:/g' $repo_file

      # Install dnf-plugins core to allow for config-manager
      yum install dnf-plugins-core -y
      echo "Installed dnf-plugins-core"

      # Add our .repo file using config-manager
      dnf config-manager --add-repo $repo_file
      echo "Added .repo file"

      # Install python3-rhmsg
      dnf install -y \
      --setopt=deltarpm=0 \
      --setopt=install_weak_deps=false \
      --setopt=tsflags=nodocs \
      python3-rhmsg
      dnf clean all
      echo "Installed rhmsg"
  fi
}
main
