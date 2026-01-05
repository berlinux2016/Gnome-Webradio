Name:           webradio-player
Version:        1.2.3
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
%{_datadir}/webradio/webradio.css

%post
/usr/bin/glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || :
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%postun
/usr/bin/glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || :
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%changelog
* Sun Jan 05 2025 DaHooL <089mobil@gmail.com> - 1.2.3-1
- Redesigned UI to match Nautilus/GNOME Files style
- Nautilus-style gray sidebar with proper GNOME colors
- Updated typography with Cantarell font and proper sizes
- Improved button styling (6px border-radius, proper hover effects)
- Enhanced list rows with subtle hover effects matching Nautilus
- Smoother animations with cubic-bezier transitions
- Better visual hierarchy with proper font weights

* Sun Jan 05 2025 DaHooL <089mobil@gmail.com> - 1.2.2-1
- Improved automatic reconnection for network changes (VPN, WiFi switching)
- First reconnect attempt now happens almost immediately (50ms) for fast resume
- Exponential backoff: 50ms, 500ms, 1s, 2s, 4s, 8s, then 10s intervals
- Increased max reconnect attempts from 5 to 15 for better reliability
- German reconnection status messages

* Sun Jan 05 2025 DaHooL <089mobil@gmail.com> - 1.2.1-1
- Prevent system suspend/standby while audio stream is playing
- Added GNOME Session Manager integration to inhibit idle/suspend during playback

* Sat Jan 04 2025 DaHooL <089mobil@gmail.com> - 1.2.0-1
- Fixed About dialog icon display
- Renamed "YouTube Music" to "YouTube Search" for trademark compliance
- Automatic stream reconnection on network changes (VPN connect/disconnect)
- Fixed window not showing when clicking app icon in Dash while running in background
- Improved MPRIS2 media controls reliability
- Fixed station name not showing in player bar when metadata updates
- More compact homepage layout
- Updated GitHub repository URLs
- Updated application ID to org.webradio.Player throughout

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
