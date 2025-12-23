# Maintainer: WebRadio Team <info@webradio.app>
pkgname=webradio-player
pkgver=1.0.0
pkgrel=1
pkgdesc="Modern Internet Radio Player for Linux"
arch=('any')
url="https://github.com/webradio/webradio-player"
license=('GPL3')
depends=(
    'python>=3.10'
    'python-gobject>=3.42.0'
    'gtk4'
    'libadwaita'
    'gstreamer'
    'gst-plugins-base'
    'gst-plugins-good'
    'gst-plugins-bad'
    'python-requests>=2.28.0'
    'python-pillow>=9.0.0'
)
makedepends=(
    'python-setuptools'
    'python-build'
    'python-installer'
    'python-wheel'
)
optdepends=(
    'gst-plugins-ugly: Additional codec support'
    'gst-libav: Additional codec support'
    'libayatana-appindicator: System tray support (recommended)'
    'libappindicator-gtk3: System tray support (alternative)'
    'gnome-shell-extension-appindicator: System tray for GNOME'
)

pkgver() {
    echo "1.0.0"
}

build() {
    cd "${startdir}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${startdir}"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Install desktop file
    install -Dm644 data/webradio.desktop \
        "${pkgdir}/usr/share/applications/webradio.desktop"

    # Install icons
    install -Dm644 data/icons/webradio.svg \
        "${pkgdir}/usr/share/icons/hicolor/scalable/apps/webradio.svg"
    install -Dm644 data/icons/webradio.png \
        "${pkgdir}/usr/share/icons/hicolor/256x256/apps/webradio.png"

    # Install appdata
    install -Dm644 data/webradio.appdata.xml \
        "${pkgdir}/usr/share/metainfo/webradio.appdata.xml"

    # Install license
    install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
