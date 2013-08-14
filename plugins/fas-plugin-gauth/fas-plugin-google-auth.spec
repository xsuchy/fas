%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           fas-plugin-google-authenticator
Version:        0.1
Release:        1%{?dist}
Summary:        Google Authenticator plugin for FAS2

Group:          Development/Languages
License:        GPLv2
URL:            https://github.com/fedora-infra/fas/
Source0:        fas-plugin-google-auth-%{version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

BuildArch:      noarch
BuildRequires:  python-devel TurboGears
%if 0%{?fedora} >= 8
BuildRequires:  python-setuptools-devel
%else
BuildRequires:  python-setuptools
%endif
Requires:       fas >= 0.8.6
Requires:       python-totpcgi

%description
Google Authenticator plugin for FAS2

%prep
%setup -q


%build
%{__python} setup.py build


%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install --skip-build --root %{buildroot}

 
%clean
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root,-)
#%doc docs/*
%{python_sitelib}/fas_gauth
%{python_sitelib}/*.egg-info


%changelog
* Wed Aug 14 2013 Xavier Lamien <laxathom@lxtnow.net> 0.1-1
- Initial upstream release.
