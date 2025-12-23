Name:           webradio-player
Version:        1.1.0
Release:        1%{?dist}
Summary:        Modern Internet Radio Player for Linux

License:        GPL-3.0-or-later
URL:            https://github.com/berlinux2016/Gnome-Webradio
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

Requires:       python3 >= 3.10
Requires:       python3-gobject >= 3.42.0
Requires:       python3-cairo >= 1.20.0
Requires:       gtk4 >= 4.0
Requires:       libadwaita >= 1.0
Requires:       gstreamer1 >= 1.0
Requires:       gstreamer1-plugins-base
Requires:       gstreamer1-plugins-good
Requires:       gstreamer1-plugins-bad-free
Requires:       python3-requests >= 2.28.0
Requires:       python3-pillow >= 9.0.0
Requires:       python3-dbus >= 1.2.0

%description
WebRadio Player is a modern, feature-rich internet radio player for Linux
desktop environments. It provides access to thousands of radio stations
from around the world through the Radio Browser API.

Features:
- Browse and search thousands of internet radio stations
- Wildcard search support for finding stations
- Create and manage your favorite stations
- Display station logos and metadata
- System tray integration for Cinnamon/GNOME
- Modern GTK4/Libadwaita interface

%prep
# Python sdist creates webradio_player-VERSION (with underscore)
%autosetup -n webradio_player-%{version}

%build
%py3_build

%install
%py3_install

# Install desktop file
desktop-file-install \
    --dir=%{buildroot}%{_datadir}/applications \
    data/org.webradio.Player.desktop

# Install icons
install -Dm644 data/icons/org.webradio.Player.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/org.webradio.Player.svg
install -Dm644 data/icons/org.webradio.Player.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/org.webradio.Player.png

# Install appdata
install -Dm644 data/org.webradio.Player.appdata.xml \
    %{buildroot}%{_datadir}/metainfo/org.webradio.Player.appdata.xml

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.webradio.Player.desktop
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/org.webradio.Player.appdata.xml

%files
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/webradio
%{python3_sitelib}/webradio/
%{python3_sitelib}/webradio_player-*.egg-info/
%{_datadir}/applications/org.webradio.Player.desktop
%{_datadir}/icons/hicolor/scalable/apps/org.webradio.Player.svg
%{_datadir}/icons/hicolor/256x256/apps/org.webradio.Player.png
%{_datadir}/metainfo/org.webradio.Player.appdata.xml
%{_datadir}/glib-2.0/schemas/org.webradio.Player.gschema.xml

%post
/usr/bin/glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || :
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%postun
/usr/bin/glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || :
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%changelog
* Wed Dec 18 2024 DaHooL <089mobil@gmail.com> - 1.1.0-1
- Real-time search while typing (debounced, 500ms delay)
- Now Playing info dialog with detailed track information
- Info button in player bar for metadata display
- Minimize to tray functionality when station is playing
- Desktop notifications on minimize
- Quit option in tray menu for complete shutdown
- Enhanced metadata tracking and display
- MPRIS2 integration for GNOME media controls
- Station logo and track info displayed in notification area
- Play/Pause/Quit controls in GNOME media player widget

* Wed Dec 18 2024 DaHooL <089mobil@gmail.com> - 1.0.0-1
- Initial release of WebRadio Player
- GTK4/Libadwaita based modern UI
- Radio Browser API integration
- System tray support
- Favorites management
- Station search with wildcard support
