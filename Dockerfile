FROM registry.access.redhat.com/ubi9/ubi:9.7-1762948793@sha256:bbac76ac0310eefd6298ed3ab3c1710e1c842f1f778800de0f49e660b402bdc5

ARG SYNC2JIRA_GIT_REPO=https://github.com/release-engineering/Sync2Jira.git
ARG SYNC2JIRA_GIT_REF=main
ARG SYNC2JIRA_VERSION=

LABEL \
    name="sync2jira" \
    org.opencontainers.image.name="sync2jira" \
    description="sync2jira application" \
    org.opencontainers.image.description="sync2jira application" \
    io.k8s.description="sync2jira application" \
    vendor="Red Hat, Inc." \
    org.opencontainers.image.vendor="Red Hat, Inc." \
    license="GPLv2+" \
    org.opencontainers.image.license="GPLv2+" \
    url="$SYNC2JIRA_GIT_REPO" \
    org.opencontainers.image.url="$SYNC2JIRA_GIT_REPO" \
    release="$SYNC2JIRA_GIT_REF" \
    com.redhat.component="null" \
    build-date="" \
    distribution-scope="public"

# Installing sync2jira dependencies
RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
RUN dnf -y install \
    git \
    python3-pip \
    krb5-devel \
    python-devel \
    fedora-messaging \
    gcc \
  && dnf -y clean all

ENV SYNC2JIRA_VERSION=$SYNC2JIRA_VERSION

USER root

# Copy in license file
RUN mkdir /licenses
COPY LICENSE /licenses/LICENSE

# Create Sync2Jira folder
RUN mkdir -p /usr/local/src/sync2jira

# Copy over our repo
COPY . /usr/local/src/sync2jira

# Install deps
RUN pip3 install -r /usr/local/src/sync2jira/requirements.txt

# Grab the latest pandoc binary
RUN python3 -c 'from pathlib import Path; import pypandoc; from pypandoc.pandoc_download import download_pandoc; download_pandoc(targetfolder=Path(pypandoc.get_pandoc_path()).parent)'

# Install Sync2Jira
RUN pip3 install --no-deps -v /usr/local/src/sync2jira

USER 1001

CMD ["/usr/local/bin/sync2jira"]
