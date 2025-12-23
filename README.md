# WebRadio Player

Ein moderner Internet-Radio-Player für Linux mit GTK4 und Libadwaita.

![WebRadio Player Logo](data/icons/org.webradio.Player.svg)

## Features

### Internet Radio
- 🌍 **Zugriff auf tausende Radiostationen** weltweit über die Radio Browser API
- 🔍 **Leistungsstarke Suchfunktion** mit Echtzeit-Suche
- ⭐ **Favoriten-Verwaltung** - Speichern und organisieren Sie Ihre Lieblingssender
- 🖼️ **Logo-Anzeige** für Radiostationen
- 📊 **Qualitätsanzeige** - Codec und Bitrate Information
- 📜 **Verlauf** - Zuletzt gespielte Sender

### YouTube Suche
- 🎵 **YouTube Integration** - Suchen und abspielen von YouTube Musik
- 🔍 **Video-Suche** - Durchsuchen Sie Millionen von Videos
- 🎧 **Audio-Streaming** - Direktes Audio-Streaming ohne Video-Download
- ⏩ **Seek-Funktion** - Vor- und Zurückspulen in Videos

### Allgemeine Features
- 🎵 **Metadaten-Anzeige** - Zeigt aktuellen Song und Interpret
- 🎚️ **Lautstärkeregelung** mit GStreamer Audio-Engine
- 🎨 **Modernes Design** mit GTK4 und Libadwaita (Spotify-inspiriertes Layout)
- 🎛️ **MPRIS2 Integration** - Native GNOME Media Controls mit Cover-Art
- 🔕 **Hintergrund-Modus** - Läuft im Hintergrund während der Wiedergabe
- 🏠 **Professional Dashboard** - Übersichtliche Startseite mit Schnellzugriff

## Systemanforderungen

- Python 3.10 oder höher
- GTK 4.0+
- Libadwaita 1.0+
- GStreamer 1.0+
- PyGObject 3.42+
- yt-dlp (für YouTube Unterstützung)

## Installation

### Schnellstart-Skript

```bash
# Repository klonen
git clone https://github.com/berlinux2016/Gnome-Webradio.git
cd Gnome-Webradio

# Programm starten (ohne Installation)
sh webradio-start.sh
```

### RPM-Paket erstellen (Fedora, RHEL, openSUSE)

```bash
# Build-Tools installieren
sudo dnf install rpm-build rpmdevtools python3-wheel desktop-file-utils libappstream-glib

# RPM bauen (automatisches Build-Skript)
sh build-rpm.sh

# Installieren
sudo dnf install ~/rpmbuild/RPMS/noarch/webradio-player-1.1.0-1.*.rpm
```

### Aus dem Source-Code

```bash
# Repository klonen
git clone https://github.com/berlinux2016/Gnome-Webradio.git
cd Gnome-Webradio

# Abhängigkeiten installieren
pip install -r requirements.txt

# YouTube Unterstützung (optional aber empfohlen)
pip install yt-dlp

# Anwendung installieren
pip install .
```

### Direkt starten (ohne Installation)

```bash
# Startskript verwenden
sh webradio-start.sh

# Oder manuell
PYTHONPATH=src python3 src/webradio/main.py
```

## Verwendung

### Starten

Nach der Installation können Sie WebRadio Player auf folgende Weisen starten:

1. **Aus dem Anwendungsmenü**: Suchen Sie nach "WebRadio Player"
2. **Über die Kommandozeile**: `webradio`
3. **Mit Startskript**: `sh webradio-start.sh`

### Bedienung

#### Stationen suchen

1. Wählen Sie "Internet Radio" in der Seitenleiste
2. Geben Sie einen Suchbegriff in das Suchfeld ein
3. Die Ergebnisse werden automatisch in Echtzeit aktualisiert

#### Favoriten verwalten

1. Klicken Sie während der Wiedergabe auf das Stern-Symbol ⭐
2. Wechseln Sie zu "Favoriten" um Ihre Favoriten zu sehen
3. Entfernen Sie Favoriten durch erneutes Klicken des Stern-Symbols

#### YouTube durchsuchen

1. Wählen Sie "YouTube Suche" in der Seitenleiste
2. Geben Sie einen Suchbegriff ein
3. Klicken Sie auf ein Ergebnis zum Abspielen
4. Nutzen Sie die Seek-Bar zum Vor- und Zurückspulen

#### Hintergrund-Modus

- Schließen Sie das Fenster während der Wiedergabe
- Die App läuft im Hintergrund weiter
- Nutzen Sie das GNOME Media Widget zur Steuerung
- Öffnen Sie die App erneut über das Anwendungsmenü

## Abhängigkeiten

### Laufzeit-Abhängigkeiten

```bash
# Fedora
sudo dnf install python3 python3-gobject gtk4 libadwaita gstreamer1 \
                 gstreamer1-plugins-base gstreamer1-plugins-good \
                 gstreamer1-plugins-bad-free python3-requests python3-pillow \
                 python3-dbus

# Ubuntu/Debian
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
                 gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
                 gstreamer1.0-plugins-bad python3-requests python3-pil \
                 python3-dbus

# Arch Linux
sudo pacman -S python python-gobject gtk4 libadwaita gstreamer \
               gst-plugins-base gst-plugins-good gst-plugins-bad \
               python-requests python-pillow python-dbus
```

### Optionale Abhängigkeiten

```bash
# Für YouTube Unterstützung (empfohlen)
pip install yt-dlp

# Für zusätzliche Audio-Codecs
sudo dnf install gstreamer1-plugins-ugly-free gstreamer1-libav  # Fedora
sudo apt install gstreamer1.0-plugins-ugly gstreamer1.0-libav  # Ubuntu/Debian
sudo pacman -S gst-plugins-ugly gst-libav  # Arch
```

## Konfiguration

Die Konfigurationsdateien werden in `~/.config/webradio/` gespeichert:

- `favorites.json`: Ihre Favoriten-Stationen
- `history.json`: Verlauf der gespielten Sender

## Fehlerbehebung

### Audio wird nicht abgespielt

1. Überprüfen Sie, ob GStreamer installiert ist: `gst-launch-1.0 --version`
2. Testen Sie Ihre Audio-Ausgabe: `gst-launch-1.0 audiotestsrc ! autoaudiosink`
3. Installieren Sie zusätzliche GStreamer-Plugins

### Keine Sender werden angezeigt

1. Überprüfen Sie Ihre Internetverbindung
2. Die Radio Browser API könnte temporär nicht verfügbar sein
3. Prüfen Sie die Konsolen-Ausgabe für Fehlermeldungen: `webradio` (im Terminal)

### YouTube funktioniert nicht

1. Stellen Sie sicher, dass yt-dlp installiert ist: `pip install yt-dlp`
2. Aktualisieren Sie yt-dlp: `pip install --upgrade yt-dlp`
3. Prüfen Sie die Konsolen-Ausgabe für Fehlermeldungen

## Entwicklung

### Projektstruktur

```
webradio/
├── src/webradio/          # Hauptquellcode
│   ├── main.py            # Einstiegspunkt
│   ├── application.py     # GTK Application
│   ├── window.py          # Hauptfenster
│   ├── player.py          # GStreamer Audio-Player
│   ├── radio_api.py       # Radio Browser API Client
│   ├── favorites.py       # Favoriten-Verwaltung
│   ├── history.py         # Verlaufs-Verwaltung
│   ├── youtube_music.py   # YouTube Integration
│   ├── mpris.py           # MPRIS2 Media Controls
│   ├── i18n.py            # Internationalisierung (DE/EN)
│   └── tray_icon.py       # System Tray Integration
├── data/                  # Ressourcen
│   ├── icons/             # Anwendungs-Icons
│   ├── org.webradio.Player.desktop   # Desktop-Datei
│   ├── webradio.css       # Stylesheet
│   ├── org.webradio.Player.appdata.xml  # AppStream Metadaten
│   └── org.webradio.Player.gschema.xml  # GSettings Schema
├── webradio.spec          # RPM-Spec-Datei
├── setup.py               # Python Setup-Skript
├── build-rpm.sh           # Automatisches RPM-Build-Skript
└── webradio-start.sh      # Schnellstart-Skript
```

### Beitragen

Beiträge sind willkommen! Bitte:

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committen Sie Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Pushen Sie zum Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

## Lizenz

Dieses Projekt ist unter der GPL-3.0 Lizenz lizenziert - siehe die [LICENSE](LICENSE) Datei für Details.

## Danksagungen

- [Radio Browser API](https://www.radio-browser.info/) für die großartige kostenlose Radio-Datenbank
- [GTK](https://www.gtk.org/) und [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) für das UI-Framework
- [GStreamer](https://gstreamer.freedesktop.org/) für die Audio-Engine
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) für YouTube Integration
- Alle Contributor und Radio-Hörer!

## Support

- **Issues**: [GitHub Issues](https://github.com/berlinux2016/Gnome-Webradio/issues)
- **Homepage**: [GitHub Repository](https://github.com/berlinux2016/Gnome-Webradio)

---

**Viel Spaß beim Hören! 🎵📻**
