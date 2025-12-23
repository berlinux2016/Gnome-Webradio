"""Internationalization support for WebRadio Player"""

import gettext
import os
import locale
from pathlib import Path

# Translations dictionary
TRANSLATIONS = {
    'en': {
        # Application
        'app_name': 'WebRadio Player',
        'app_description': 'Modern Internet Radio Player for Linux',

        # Menu
        'menu_preferences': 'Preferences',
        'menu_about': 'About',
        'menu_quit': 'Quit',

        # Navigation Sections
        'section_home': 'HOME',
        'section_library': 'YOUR LIBRARY',
        'section_online': 'ONLINE',

        # Navigation (Sidebar)
        'Home': 'Home',
        'Now Playing': 'Now Playing',
        'Search': 'Search',

        # Library
        'Playlists': 'Playlists',
        'Local Music': 'Local Music',
        'Artists': 'Artists',
        'Albums': 'Albums',

        # Online
        'Internet Radio': 'Internet Radio',
        'YouTube Search': 'YouTube Search',
        'Discover': 'Discover',
        'Favorites': 'Favorites',
        'History': 'History',

        # Tabs
        'tab_discover': 'Discover',
        'tab_favorites': 'Favorites',

        # Search
        'search_placeholder': 'Search stations (use * for wildcard)...',
        'search_button': 'Search',
        'search_favorites': 'Search favorites...',

        # Country filter
        'Country:': 'Country:',
        'All Countries': 'All Countries',

        # Filter buttons
        'filter_top_voted': 'Top Voted',
        'filter_rock': 'Rock',
        'filter_pop': 'Pop',
        'filter_jazz': 'Jazz',
        'filter_classical': 'Classical',
        'filter_news': 'News',

        # Placeholders
        'placeholder_loading': 'Loading radio stations...',
        'placeholder_click_top_voted': "Click 'Top Voted' to load stations",
        'placeholder_no_favorites': 'No favorites yet\nClick the ♥ button to add stations',
        'No Stations Loaded': 'No Stations Loaded',
        'Click "Top Voted" to browse popular stations': 'Click "Top Voted" to browse popular stations',
        'No Favorites': 'No Favorites',
        'Click the star icon on a station to add it to favorites': 'Click the star icon on a station to add it to favorites',
        'Recently Played': 'Recently Played',
        'Clear History': 'Clear History',

        # Player controls
        'tooltip_favorite': 'Add to favorites',
        'tooltip_remove_favorite': 'Remove from favorites',
        'tooltip_play_pause': 'Play/Pause',
        'tooltip_stop': 'Stop',
        'no_station_playing': 'No station playing',
        'No Station Playing': 'No Station Playing',
        'Add to favorites': 'Add to favorites',
        'Play/Pause': 'Play/Pause',
        'Stop': 'Stop',
        'Record Stream': 'Record Stream',
        'Sleep Timer': 'Sleep Timer',
        'Start Recording': 'Start Recording',
        'Stop Recording': 'Stop Recording',

        # Context menu
        'context_delete_favorite': 'Delete from Favorites',
        'context_play': 'Play',
        'context_add_favorite': 'Add to Favorites',

        # Buttons
        'button_clear_all': 'Clear All',
        'button_ok': 'OK',
        'button_cancel': 'Cancel',

        # Dialogs
        'dialog_clear_favorites_title': 'Clear All Favorites?',
        'dialog_clear_favorites_body': 'This will remove all stations from your favorites list.',

        # Status messages
        'loading_stations': 'Loading stations...',
        'loaded_stations': 'Loaded {count} stations',
        'playing': 'Playing: {name}',
        'deleted_favorite': 'Deleted from favorites: {name}',

        # Time ago
        'time_just_now': 'Just now',
        'time_day': 'day',
        'time_days': 'days',
        'time_hour': 'hour',
        'time_hours': 'hours',
        'time_minute': 'minute',
        'time_minutes': 'minutes',
        'time_ago': 'ago',

        # About dialog
        'about_developers': 'Developed by DaHooL',
        'about_copyright': '© 2025 DaHooL',
        'about_website': 'https://github.com/dahool/webradio-player',

        # Local Music
        'local_music_title': 'Local Music Library',
        'add_music_folder': 'Add Music Folder',
        'scan_library': 'Scan Library',
        'scanning_library': 'Scanning...',
        'no_music_folders': 'No music folders configured',
        'add_folder_hint': 'Click "Add Music Folder" to start',
        'tracks_found': '{count} tracks found',
        'artist_column': 'Artist',
        'title_column': 'Title',
        'album_column': 'Album',
        'duration_column': 'Duration',

        # Playlists
        'playlists_title': 'Your Playlists',
        'create_playlist': 'Create Playlist',
        'no_playlists': 'No playlists yet',
        'create_playlist_hint': 'Click "Create Playlist" to start',

        # Artists
        'artists_title': 'Artists',
        'no_artists': 'No artists found',
        'all_artists': 'All Artists',

        # Albums
        'albums_title': 'Albums',
        'no_albums': 'No albums found',
        'all_albums': 'All Albums',

        # YouTube Search
        'youtube_title': 'YouTube Search',
        'youtube_search': 'Search YouTube',
        'youtube_not_implemented': 'YouTube integration coming soon',
    },
    'de': {
        # Application
        'app_name': 'WebRadio Player',
        'app_description': 'Moderner Internet-Radio-Player für Linux',

        # Menu
        'menu_preferences': 'Einstellungen',
        'menu_about': 'Über',
        'menu_quit': 'Beenden',

        # Navigation Sections
        'section_home': 'START',
        'section_library': 'DEINE BIBLIOTHEK',
        'section_online': 'ONLINE',

        # Navigation (Sidebar)
        'Home': 'Start',
        'Now Playing': 'Aktuell',
        'Search': 'Suche',

        # Library
        'Playlists': 'Playlists',
        'Local Music': 'Lokale Musik',
        'Artists': 'Künstler',
        'Albums': 'Alben',

        # Online
        'Internet Radio': 'Internet Radio',
        'YouTube Search': 'YouTube Suche',
        'Discover': 'Entdecken',
        'Favorites': 'Favoriten',
        'History': 'Verlauf',

        # Tabs
        'tab_discover': 'Entdecken',
        'tab_favorites': 'Favoriten',

        # Search
        'search_placeholder': 'Sender suchen (verwende * als Platzhalter)...',
        'search_button': 'Suchen',
        'search_favorites': 'Favoriten durchsuchen...',

        # Country filter
        'Country:': 'Land:',
        'All Countries': 'Alle Länder',

        # Filter buttons
        'filter_top_voted': 'Top Bewertet',
        'filter_rock': 'Rock',
        'filter_pop': 'Pop',
        'filter_jazz': 'Jazz',
        'filter_classical': 'Klassik',
        'filter_news': 'Nachrichten',

        # Placeholders
        'placeholder_loading': 'Lade Radiosender...',
        'placeholder_click_top_voted': "Klicken Sie auf 'Top Bewertet' um Sender zu laden",
        'placeholder_no_favorites': 'Noch keine Favoriten\nKlicken Sie auf ♥ um Sender hinzuzufügen',
        'No Stations Loaded': 'Keine Sender geladen',
        'Click "Top Voted" to browse popular stations': 'Klicken Sie auf "Top Bewertet" um beliebte Sender zu durchsuchen',
        'No Favorites': 'Keine Favoriten',
        'Click the star icon on a station to add it to favorites': 'Klicken Sie auf das Stern-Symbol, um einen Sender zu Favoriten hinzuzufügen',
        'Recently Played': 'Kürzlich abgespielt',
        'Clear History': 'Verlauf löschen',

        # Player controls
        'tooltip_favorite': 'Zu Favoriten hinzufügen',
        'tooltip_remove_favorite': 'Von Favoriten entfernen',
        'tooltip_play_pause': 'Abspielen/Pause',
        'tooltip_stop': 'Stopp',
        'no_station_playing': 'Kein Sender wird abgespielt',
        'No Station Playing': 'Kein Sender wird abgespielt',
        'Add to favorites': 'Zu Favoriten hinzufügen',
        'Play/Pause': 'Abspielen/Pause',
        'Stop': 'Stopp',
        'Record Stream': 'Stream aufnehmen',
        'Sleep Timer': 'Sleep-Timer',
        'Start Recording': 'Aufnahme starten',
        'Stop Recording': 'Aufnahme stoppen',

        # Context menu
        'context_delete_favorite': 'Aus Favoriten löschen',
        'context_play': 'Abspielen',
        'context_add_favorite': 'Zu Favoriten hinzufügen',

        # Buttons
        'button_clear_all': 'Alle löschen',
        'button_ok': 'OK',
        'button_cancel': 'Abbrechen',

        # Dialogs
        'dialog_clear_favorites_title': 'Alle Favoriten löschen?',
        'dialog_clear_favorites_body': 'Dies entfernt alle Sender aus Ihrer Favoritenliste.',

        # Status messages
        'loading_stations': 'Lade Sender...',
        'loaded_stations': '{count} Sender geladen',
        'playing': 'Spielt ab: {name}',
        'deleted_favorite': 'Aus Favoriten gelöscht: {name}',

        # Time ago
        'time_just_now': 'Gerade eben',
        'time_day': 'Tag',
        'time_days': 'Tage',
        'time_hour': 'Stunde',
        'time_hours': 'Stunden',
        'time_minute': 'Minute',
        'time_minutes': 'Minuten',
        'time_ago': 'vor',

        # About dialog
        'about_developers': 'Entwickelt von DaHooL',
        'about_copyright': '© 2025 DaHooL',
        'about_website': 'https://github.com/dahool/webradio-player',

        # Local Music
        'local_music_title': 'Lokale Musikbibliothek',
        'add_music_folder': 'Musikordner hinzufügen',
        'scan_library': 'Bibliothek scannen',
        'scanning_library': 'Scanne...',
        'no_music_folders': 'Keine Musikordner konfiguriert',
        'add_folder_hint': 'Klicken Sie auf "Musikordner hinzufügen" um zu starten',
        'tracks_found': '{count} Titel gefunden',
        'artist_column': 'Künstler',
        'title_column': 'Titel',
        'album_column': 'Album',
        'duration_column': 'Dauer',

        # Playlists
        'playlists_title': 'Deine Playlists',
        'create_playlist': 'Playlist erstellen',
        'no_playlists': 'Noch keine Playlists',
        'create_playlist_hint': 'Klicke auf "Playlist erstellen" um zu starten',

        # Artists
        'artists_title': 'Künstler',
        'no_artists': 'Keine Künstler gefunden',
        'all_artists': 'Alle Künstler',

        # Albums
        'albums_title': 'Alben',
        'no_albums': 'Keine Alben gefunden',
        'all_albums': 'Alle Alben',

        # YouTube Search
        'youtube_title': 'YouTube Suche',
        'youtube_search': 'YouTube durchsuchen',
        'youtube_not_implemented': 'YouTube Integration kommt bald',
    }
}

class I18n:
    """Simple i18n handler"""

    def __init__(self):
        # Try to get system locale
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                # Extract language code (e.g., 'de_DE' -> 'de')
                lang = system_locale.split('_')[0].lower()
            else:
                lang = 'en'
        except:
            lang = 'en'

        # Default to English if language not supported
        self.lang = lang if lang in TRANSLATIONS else 'en'
        print(f"Language: {self.lang}")

    def _(self, key: str, **kwargs) -> str:
        """Get translated string"""
        text = TRANSLATIONS[self.lang].get(key, TRANSLATIONS['en'].get(key, key))

        # Format with kwargs if provided
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

    def set_language(self, lang: str):
        """Set language manually"""
        if lang in TRANSLATIONS:
            self.lang = lang
            print(f"Language changed to: {lang}")

# Global translator instance
_translator = I18n()

def _(key: str, **kwargs) -> str:
    """Global translation function"""
    return _translator._(key, **kwargs)

def set_language(lang: str):
    """Set language globally"""
    _translator.set_language(lang)

def get_language() -> str:
    """Get current language"""
    return _translator.lang
