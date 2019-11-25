%{!?_licensedir: %global license %%doc}

%global modname sync2jira
%global sum     Sync pagure and github issues to jira, via fedmsg
%global upstream_version 1.7

Name:               sync2jira
Version:            1.7
Release:            7%{?dist}
Summary:            %{sum}

License:            LGPLv2+
URL:                https://pypi.io/pypi/sync2jira
Source0:            https://pypi.io/packages/source/s/%{modname}/%{modname}-%{upstream_version}.tar.gz
BuildArch:          noarch

BuildRequires:      systemd

BuildRequires:      python3-devel
BuildRequires:      python3-setuptools
BuildRequires:      python3-fedmsg-core
BuildRequires:      python3-github3py
BuildRequires:      python3-requests
BuildRequires:      python3-nose
BuildRequires:      python3-pytest
BuildRequires:      python3-mock
BuildRequires:      python3-jira
BuildRequires:      python3-arrow

%description
This is a process that listens to activity on upstream repos on pagure and
github via fedmsg, and syncs new issues there to a Jira instance elsewhere.

Configuration is in /etc/fedmsg.d/. You can maintain a mapping there that
allows you to match one upstream repo (say, 'pungi' on pagure) to a downstream
project/component pair in Jira (say, 'COMPOSE', and 'Pungi').

%package -n python3-%{modname}
Summary:            %{sum}
%{?python_provide:%python_provide python3-%{modname}}

Requires:           python3-requests
Requires:           python3-jira
Requires:           python3-fedmsg-core
Requires:           python3-github3py

%description -n python3-%{modname}
This is a process that listens to activity on upstream repos on pagure and
github via fedmsg, and syncs new issues there to a Jira instance elsewhere.

Configuration is in /etc/fedmsg.d/. You can maintain a mapping there that
allows you to match one upstream repo (say, 'pungi' on pagure) to a downstream
project/component pair in Jira (say, 'COMPOSE', and 'Pungi').

%prep
%setup -q -n %{modname}-%{upstream_version}

# The egg name is all screwy here...
sed -i '/jira/d' requirements.txt

# Remove shebang from main.py
sed -i '/\/usr\/bin\/env/d' sync2jira/main.py

# Remove upstream's egg-info
rm -rf *.egg*

%build
%py3_build

%install
%py3_install

%{__mkdir_p} %{buildroot}%{_unitdir}
%{__install} -pm644 systemd/sync2jira.service \
    %{buildroot}%{_unitdir}/sync2jira.service

%check
%{__python3} setup.py test

%files -n python3-%{modname}
%doc README.rst
%license LICENSE
%{python3_sitelib}/%{modname}/
%{python3_sitelib}/%{modname}-*.egg*

# If built with py3, provide executables in py3 subpackage
%{_bindir}/sync2jira
%{_bindir}/sync2jira-list-managed-urls
%{_bindir}/sync2jira-close-duplicates
%{_unitdir}/sync2jira.service
