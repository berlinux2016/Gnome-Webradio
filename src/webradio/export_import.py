"""
Export/Import Manager for Gnome Web Radio

This module provides functionality to export and import station lists
in standard formats (OPML and M3U) for backup, sharing, and cross-app compatibility.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from webradio.logger import get_logger

logger = get_logger(__name__)


class ExportImportManager:
    """
    Manages export and import of station lists in various formats.

    Supported formats:
    - OPML: XML-based format used by many podcast/radio apps
    - M3U: Simple playlist format compatible with VLC, etc.
    """

    def __init__(self):
        """Initialize the export/import manager."""
        logger.info("ExportImportManager initialized")

    def export_to_opml(self, stations: List[Dict], file_path: str) -> bool:
        """
        Export stations to OPML format.

        Args:
            stations: List of station dictionaries
            file_path: Path to save the OPML file

        Returns:
            bool: True if export succeeded, False otherwise
        """
        try:
            # Create OPML structure
            opml = ET.Element('opml', version='2.0')

            # Head section
            head = ET.SubElement(opml, 'head')
            title = ET.SubElement(head, 'title')
            title.text = 'WebRadio Player - Exported Stations'
            date_created = ET.SubElement(head, 'dateCreated')
            date_created.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

            # Body section
            body = ET.SubElement(opml, 'body')

            # Add stations as outline elements
            for station in stations:
                outline = ET.SubElement(body, 'outline')
                outline.set('type', 'link')
                outline.set('text', station.get('name', 'Unknown Station'))
                outline.set('url', station.get('url_resolved', station.get('url', '')))

                # Add optional attributes
                if 'homepage' in station:
                    outline.set('htmlUrl', station['homepage'])
                if 'favicon' in station:
                    outline.set('icon', station['favicon'])
                if 'tags' in station:
                    outline.set('category', station['tags'])
                if 'country' in station:
                    outline.set('country', station['country'])
                if 'language' in station:
                    outline.set('language', station['language'])

            # Write to file with pretty formatting
            tree = ET.ElementTree(opml)
            ET.indent(tree, space='  ')
            tree.write(file_path, encoding='utf-8', xml_declaration=True)

            logger.info(f"Exported {len(stations)} stations to OPML: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to OPML: {e}")
            return False

    def export_to_m3u(self, stations: List[Dict], file_path: str) -> bool:
        """
        Export stations to M3U playlist format.

        Args:
            stations: List of station dictionaries
            file_path: Path to save the M3U file

        Returns:
            bool: True if export succeeded, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write M3U header
                f.write('#EXTM3U\n')

                # Write each station
                for station in stations:
                    name = station.get('name', 'Unknown Station')
                    url = station.get('url_resolved', station.get('url', ''))

                    # Extended M3U format with station info
                    # Format: #EXTINF:duration,artist - title
                    # For radio streams, duration is -1 (infinite)
                    f.write(f'#EXTINF:-1,{name}\n')

                    # Add additional metadata as comments
                    if 'tags' in station:
                        f.write(f'#EXTGENRE:{station["tags"]}\n')
                    if 'homepage' in station:
                        f.write(f'#EXTALB:{station["homepage"]}\n')

                    # Write stream URL
                    f.write(f'{url}\n')

            logger.info(f"Exported {len(stations)} stations to M3U: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to M3U: {e}")
            return False

    def import_from_opml(self, file_path: str) -> Optional[List[Dict]]:
        """
        Import stations from OPML format.

        Args:
            file_path: Path to the OPML file

        Returns:
            List of station dictionaries, or None if import failed
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            stations = []

            # Find all outline elements (stations)
            body = root.find('body')
            if body is None:
                logger.warning("OPML file has no body element")
                return []

            for outline in body.findall('outline'):
                # Extract station data from OPML attributes
                station = {
                    'name': outline.get('text', 'Unknown Station'),
                    'url': outline.get('url', ''),
                    'url_resolved': outline.get('url', ''),
                }

                # Add optional fields
                if outline.get('htmlUrl'):
                    station['homepage'] = outline.get('htmlUrl')
                if outline.get('icon'):
                    station['favicon'] = outline.get('icon')
                if outline.get('category'):
                    station['tags'] = outline.get('category')
                if outline.get('country'):
                    station['country'] = outline.get('country')
                if outline.get('language'):
                    station['language'] = outline.get('language')

                # Only add if we have a valid URL
                if station['url']:
                    stations.append(station)

            logger.info(f"Imported {len(stations)} stations from OPML: {file_path}")
            return stations

        except Exception as e:
            logger.error(f"Failed to import from OPML: {e}")
            return None

    def import_from_m3u(self, file_path: str) -> Optional[List[Dict]]:
        """
        Import stations from M3U playlist format.

        Args:
            file_path: Path to the M3U file

        Returns:
            List of station dictionaries, or None if import failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            stations = []
            current_station = {}

            for line in lines:
                line = line.strip()

                # Skip empty lines and M3U header
                if not line or line == '#EXTM3U':
                    continue

                # Parse extended info line
                if line.startswith('#EXTINF:'):
                    # Format: #EXTINF:duration,name
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        current_station['name'] = parts[1].strip()

                # Parse genre metadata
                elif line.startswith('#EXTGENRE:'):
                    current_station['tags'] = line.split(':', 1)[1].strip()

                # Parse homepage metadata
                elif line.startswith('#EXTALB:'):
                    current_station['homepage'] = line.split(':', 1)[1].strip()

                # Parse stream URL (non-comment line)
                elif not line.startswith('#'):
                    current_station['url'] = line
                    current_station['url_resolved'] = line

                    # Add station to list if it has required fields
                    if 'name' not in current_station:
                        current_station['name'] = 'Unknown Station'

                    stations.append(current_station)
                    current_station = {}

            logger.info(f"Imported {len(stations)} stations from M3U: {file_path}")
            return stations

        except Exception as e:
            logger.error(f"Failed to import from M3U: {e}")
            return None


def create_export_import_manager() -> ExportImportManager:
    """
    Factory function to create an export/import manager.

    Returns:
        ExportImportManager: Configured export/import manager
    """
    return ExportImportManager()
