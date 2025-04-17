import re
import os
from pathlib import Path

def sanitize_filename(name):
    """Removes or replaces characters invalid for filenames."""
    # Remove leading/trailing whitespace
    name = name.strip()
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove characters that are problematic in filenames
    # (adjust the set of characters based on strictness needed)
    invalid_chars = r'[\\/*?:"<>|]'
    name = re.sub(invalid_chars, '', name)
    # Prevent empty names or names consisting only of invalid chars
    if not name:
        name = "untitled_schema"
    # Ensure it doesn't end with a dot or space (problematic on some systems)
    name = re.sub(r'[. ]+$', '', name)
    # Handle reserved names if necessary (e.g., CON, PRN on Windows, though less relevant on Linux)
    # For simplicity, we'll skip this for now on Linux target.
    if not name: # Check again after potential removal of trailing dots/spaces
        name = "untitled_schema_final"
    return name

def validate_schema_paths(schema_data):
    """
    Checks if all source paths and the destination path in a schema exist.

    Args:
        schema_data (dict): Dictionary containing 'sources' (list) and 'destination' (str).

    Returns:
        bool: True if all paths are valid, False otherwise.
        list: A list of invalid paths found.
    """
    invalid_paths = []
    if not schema_data:
        return False, ["Schema data is empty"]

    sources = schema_data.get('sources', [])
    destination = schema_data.get('destination')

    if not isinstance(sources, list):
         invalid_paths.append("Sources format is invalid")
         sources = [] # Prevent further errors

    if not destination or not isinstance(destination, str):
        invalid_paths.append("Destination path is missing or invalid")
    elif not Path(destination).exists():
        invalid_paths.append(f"Destination: {destination}")

    for src in sources:
        if not isinstance(src, str) or not Path(src).exists():
            invalid_paths.append(f"Source: {src}")

    return not invalid_paths, invalid_paths
