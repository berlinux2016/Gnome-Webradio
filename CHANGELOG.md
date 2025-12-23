# WebRadio Player - Changelog

## Version 1.1.0 (18. Dezember 2024)

### 🚀 Neue Features

**🔍 Echtzeit-Suche während des Tippens**
- ✅ Automatische Suche startet 500ms nach letztem Tastendruck
- ✅ Debouncing verhindert zu viele API-Aufrufe
- ✅ Bei leerem Suchfeld werden Top-Sender geladen
- ✅ Keine Enter-Taste mehr nötig
- ✅ Flüssiges und modernes Benutzererlebnis wie Google/Spotify

**ℹ️ Now Playing Info Dialog**
- ✅ Info-Button (ℹ️) im Player-Bar hinzugefügt
- ✅ Detaillierte Track-Informationen anzeigen
- ✅ Professionell gestalteter Dialog mit mehreren Abschnitten:
  - 🎵 Currently Playing (Titel, Künstler, Album)
  - 📻 Station Information (Land, Region, Sprache, Tags)
  - 🔧 Technical Details (Codec, Bitrate, URLs mit Copy-Button)
  - 📊 Statistics (Votes, Total Clicks)
- ✅ Großes 128x128 Sender-Logo
- ✅ Scrollbarer Content
- ✅ URLs direkt in Zwischenablage kopierbar

**🎯 Minimize to Tray Funktionalität**
- ✅ Intelligentes Verhalten beim Fenster-Schließen:
  - Sender läuft → Minimiert zum System Tray
  - Kein Sender → Programm beendet sich
- ✅ Desktop-Benachrichtigung beim Minimieren
- ✅ Musik läuft im Hintergrund weiter
- ✅ GNOME Top Bar Integration
- ✅ Vollständiges Tray-Menü:
  - Show/Hide Window
  - Play/Pause
  - Stop
  - **Quit WebRadio** (komplettes Beenden)
- ✅ Tooltip zeigt aktuellen Sender

**🎵 Erweiterte Metadata-Verwaltung**
- ✅ `current_tags` Dictionary im Player
- ✅ `get_current_tags()` Methode
- ✅ Automatische Updates bei Tag-Änderungen
- ✅ Persistente Metadaten während Wiedergabe

**🎛️ MPRIS2 Integration (GNOME Media Controls)**
- ✅ Native Integration in GNOME Notification Area
- ✅ Anzeige von Sender-Logo und aktuellen Track-Informationen
- ✅ Play/Pause/Stop Controls direkt aus der Notification Area
- ✅ Quit-Button zum kompletten Beenden der App
- ✅ Automatische Metadaten-Updates bei Song-Wechsel
- ✅ D-Bus basierte Standard-Implementierung

### 📝 Dokumentation

- 📄 [FEATURES_REALTIME_SEARCH_INFO.md](FEATURES_REALTIME_SEARCH_INFO.md) - Echtzeit-Suche & Info-Dialog
- 📄 [MINIMIZE_TO_TRAY.md](MINIMIZE_TO_TRAY.md) - Tray-Funktionalität
- 📄 Aktualisierte README mit neuen Features

### 🔧 Technische Verbesserungen

- ✅ GTK3/GTK4 Kompatibilität für Tray-Menü
- ✅ Threadsafe Implementierung
- ✅ Memory-effizientes Debouncing
- ✅ Error-Handling für alle neuen Features

---

## Version 1.0.2 (18. Dezember 2024)

### 🎨 Hauptfeature: Neue "Now Playing" Anzeige

**Komplett überarbeitete Player-Bar:**

- ✅ **64x64 Sender-Logo** anzeige
- ✅ **Drei Informations-Zeilen:**
  1. Sender-Name (groß, prominent)
  2. Song & Künstler mit ♪ Symbol (Echtzeit-Updates)
  3. Technische Details (Land • Codec • Bitrate)
- ✅ **Separator-Linie** für klare Trennung
- ✅ **Verbesserte Controls** mit Tooltips
- ✅ **Lautstärke-Icon** hinzugefügt

**Vorher:**
```
No station playing [♥] [▶] [■] [Volume]
```

**Nachher:**
```
─────────────────────────────────────────────
[LOGO]  BBC Radio 1                    [♥][▶]
        ♪ Artist - Song Title          [■][🔊]
        United Kingdom • MP3 • 128 kbps
```

### Weitere Verbesserungen

- ✅ Asynchrones Logo-Laden (UI bleibt flüssig)
- ✅ Metadaten in separater Zeile
- ✅ Opacity-Abstufung für bessere Lesbarkeit
- ✅ Tooltips für alle Buttons
- ✅ Verbesserte Fehlerbehandlung

### Dokumentation

- 📄 Neue Datei: [NOW_PLAYING_DESIGN.md](NOW_PLAYING_DESIGN.md)
- 📄 Details zum neuen Design und Features

---

## Version 1.0.1 (17. Dezember 2024)

### 🐛 Kritische Bugfixes

**Problem: Weißes Fenster - BEHOBEN**
- ✅ window.py komplett neu geschrieben
- ✅ Vereinfachte UI-Struktur mit Gtk.Notebook
- ✅ Bessere Placeholder-Texte
- ✅ Stabilere Initialisierung

**Problem: System-Tray GTK3/GTK4 Konflikt - BEHOBEN**
- ✅ Neue GTK4-kompatible TrayIcon-Implementierung
- ✅ libayatana-appindicator Support
- ✅ Fallback ohne Tray funktioniert

**Problem: GStreamer Debug-Spam - REDUZIERT**
- ✅ GST_DEBUG auf Level 1 gesetzt
- ✅ Warnungen sind harmlos und normal

### Neue Features

- ✅ System-Tray für Cinnamon, XFCE, KDE, MATE, Budgie
- ✅ Optional: GNOME Support mit Extension
- ✅ Verbesserte Debug-Ausgaben
- ✅ Mehrere Start-Skripte (webradio-start.sh, run.sh)
- ✅ Umfangreiche Dokumentation

### Dokumentation

- 📄 [SUCCESS_SUMMARY.md](SUCCESS_SUMMARY.md) - Vollständige Änderungen
- 📄 [SYSTEM_TRAY_SETUP.md](SYSTEM_TRAY_SETUP.md) - Tray einrichten
- 📄 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Problemlösungen
- 📄 [QUICKSTART.md](QUICKSTART.md) - Schnellstart
- 📄 [WHITE_WINDOW_FIX.md](WHITE_WINDOW_FIX.md) - Debugging-Guide

### Packaging

- ✅ PKGBUILD aktualisiert mit optdepends
- ✅ Paket-Größe: 121 KB
- ✅ Installierbar mit: `sudo pacman -U webradio-player-*.pkg.tar.zst`

---

## Version 1.0.0 (Ursprüngliche Version)

### Core Features

- ✅ Radio Browser API Integration (30.000+ Sender)
- ✅ Wildcard-Suche (`*Rock*`, `Jazz*`)
- ✅ Favoriten-Verwaltung
- ✅ GStreamer Audio-Player
- ✅ GTK4/Libadwaita UI
- ✅ Genre-Filter (Rock, Pop, Jazz, Classical, News)
- ✅ Zwei Ansichten: Discover & Favorites
- ✅ Lautstärke-Regelung
- ✅ Play/Pause/Stop Steuerung

### Bekannte Probleme (behoben in 1.0.0-1)

- ❌ Weißes Fenster beim Start
- ❌ System-Tray GTK3/GTK4 Konflikt
- ❌ Zu viele GStreamer-Warnungen

---

## Upgrade-Anleitung

### Von 1.0.0-1 auf 1.0.0-2

Einfach neu installieren (Beispiel für Arch Linux):

```bash
# Altes Paket entfernen
sudo pacman -R webradio-player

# Neues Paket installieren
sudo pacman -U webradio-player-1.0.0-2-any.pkg.tar.zst
```

### Änderungen in der Konfiguration

Keine Breaking Changes - alle Einstellungen bleiben erhalten:
- ✅ Favoriten in `~/.config/webradio/favorites.json`
- ✅ Keine Migration nötig

---

## Roadmap

### Version 1.1 (Geplant)

- [ ] Logo-Caching für schnelleres Laden
- [ ] Vollständiges Tray-Menü (GTK4-kompatibel)
- [ ] Tastenkürzel (Space für Play/Pause, etc.)
- [ ] Verlauf der gespielten Sender
- [ ] Export/Import von Favoriten

### Version 1.2 (Ideen)

- [ ] Equalizer
- [ ] Aufnahme-Funktion
- [ ] Sleep-Timer
- [ ] Desktop-Lyrics
- [ ] Große "Now Playing" Ansicht
- [ ] Visualisierung/Spektrum

### Version 2.0 (Zukunft)

- [ ] Podcast-Support
- [ ] Playlist-Verwaltung
- [ ] Scrobbling (Last.fm, etc.)
- [ ] Remote Control (Smartphone-App)
- [ ] Multi-Room Audio

---

## Bekannte Einschränkungen

### GTK4 + AppIndicator

**Problem:** Rechtsklick-Menü im Tray funktioniert nicht vollständig

**Grund:** GTK4 und AppIndicator3 haben Kompatibilitätsprobleme

**Status:** Wird in zukünftiger Version mit Portal-Integration gelöst

**Workaround:**
- Fenster normal minimieren
- Tastenkürzel verwenden

### GStreamer Codec-Warnungen

**Problem:** Viele Warnungen in der Console

**Grund:** Manche Sender senden fehlerhafte Daten

**Auswirkung:** Keine - Audio funktioniert trotzdem

**Workaround:** `export GST_DEBUG=0` für stille Ausgabe

---

## Statistiken

### Codebase

- **Python-Module:** 8
- **Zeilen Code:** ~1500
- **Dokumentation:** ~3000 Zeilen
- **Paket-Größe:** 121 KB

### Features

- **Radiostationen:** 30.000+ (via Radio Browser API)
- **Unterstützte Codecs:** MP3, AAC, AAC+, OGG, FLAC
- **Desktop-Umgebungen:** Cinnamon, XFCE, KDE, MATE, Budgie, GNOME*

*mit Extension

---

**Zuletzt aktualisiert:** 18. Dezember 2024
**Aktuelle Version:** 1.1.0
