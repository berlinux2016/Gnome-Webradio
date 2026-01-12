#!/usr/bin/env python3
"""Script to refactor window.py by removing extracted classes"""

def remove_class_definitions(file_path):
    """Remove MusicTrackRow, YouTubeVideoRow, and StationRow class definitions"""

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find class boundaries
    classes_to_remove = ['MusicTrackRow', 'YouTubeVideoRow', 'StationRow']
    new_lines = []
    skip_until_next_class = False
    current_class = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if we're starting a new class
        if line.startswith('class '):
            class_name = line.split('(')[0].replace('class ', '').strip()

            if class_name in classes_to_remove:
                # Skip this class
                skip_until_next_class = True
                current_class = class_name
                print(f"Removing class: {class_name} at line {i+1}")
                i += 1
                continue
            elif skip_until_next_class:
                # We've reached the next class, stop skipping
                skip_until_next_class = False
                current_class = None

        # If not skipping, add the line
        if not skip_until_next_class:
            new_lines.append(line)

        i += 1

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Removed {len(lines) - len(new_lines)} lines")
    print(f"Original: {len(lines)} lines, New: {len(new_lines)} lines")

if __name__ == '__main__':
    file_path = 'src/webradio/window.py'
    remove_class_definitions(file_path)
    print("Done!")
