#!/usr/bin/env python3
"""Setup script for WebRadio Player"""

from setuptools import setup, find_packages
import os

def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

setup(
    name='webradio-player',
    version='1.2.0',
    description='Modern GTK4 Web Radio Player for Linux',
    long_description=read_file('README.md') if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='DaHooL',
    author_email='089mobil@gmail.com',
    url='https://github.com/berlinux2016/Gnome-Webradio',
    license='GPL-3.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'pygobject>=3.42.0',
        'requests>=2.28.0',
        'pillow>=9.0.0',
    ],
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'webradio=webradio.main:main',
        ],
    },
    data_files=[
        ('share/applications', ['data/org.webradio.Player.desktop']),
        ('share/icons/hicolor/scalable/apps', ['data/icons/org.webradio.Player.svg']),
        ('share/icons/hicolor/256x256/apps', ['data/icons/org.webradio.Player.png']),
        ('share/metainfo', ['data/org.webradio.Player.appdata.xml']),
        ('share/glib-2.0/schemas', ['data/org.webradio.Player.gschema.xml']),
        ('share/webradio', ['data/webradio.css']),
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
