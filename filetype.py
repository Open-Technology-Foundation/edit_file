#!/usr/bin/env python3
"""
filetype - Determine type of a file based on extension, shebang, or content

Usage:
  filetype filename

Arguments:
  filename - Path to the file to be evaluated

Returns:
  Outputs one of the following file types to stdout:
    - bash: Bash scripts
    - python: Python scripts
    - php: PHP scripts or HTML files
    - c: C source files
    - text: Plain text files
    - binary: Binary files

Description:
  'filetype' identifies type of file by performing the following checks:
    1. Extension Check: Determines file type based on extension.
    2. Shebang Inspection: If no recognized extension, examines shebang line.
    3. MIME Type Analysis: Utilizes 'file' command to ascertain MIME type.
    4. Binary Detection: Checks for binary signatures.
  If all checks fail, defaults to classifying the file as 'text'.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

def get_mime_type(filename: str) -> str:
  """Get MIME type of file using 'file' command"""
  if not os.path.exists(filename):
    return ""

  try:
    result = subprocess.run(
      ['file', '-b', '--mime-type', filename],
      capture_output=True,
      text=True,
      check=True
    )
    return result.stdout.strip()
  except subprocess.CalledProcessError:
    return ""

def get_file_type(filename: str) -> str:
  """Get file type description using 'file' command"""
  if not os.path.exists(filename):
    return ""

  try:
    result = subprocess.run(
      ['file', '-b', filename],
      capture_output=True,
      text=True,
      check=True
    )
    return result.stdout.strip()
  except subprocess.CalledProcessError:
    return ""

def check_shebang(filename: str) -> Optional[str]:
  """Check file's shebang line for type hints"""
  if not os.path.exists(filename):
    return None

  try:
    with open(filename, 'r', encoding='utf-8') as f:
      first_line = f.readline().strip()

    # Check for various shebangs
    if first_line in {
      "#!/bin/bash",
      "#!/usr/bin/env bash",
      "#!/usr/bin/bash",
      "#!/bin/sh",
      "#!/usr/bin/env sh",
      "#!/usr/bin/sh"
    }:
      return "bash"

    if first_line.startswith(("#!/usr/bin/python", "#!/usr/bin/env python")):
      return "python"

    if first_line in {
      "#!/usr/bin/php",
      "#!/usr/bin/env php"
    } or first_line.startswith("<?php") or first_line == "<?":
      return "php"

  except (IOError, UnicodeDecodeError):
    pass

  return None

def is_binary_file(filename: str) -> bool:
  """Check if a file is binary by looking for null bytes in the first chunk"""
  if not os.path.exists(filename):
    return False

  try:
    with open(filename, 'rb') as f:
      chunk = f.read(4096)
      return b'\x00' in chunk
  except IOError:
    return False

def get_extension_type(extension: str) -> Optional[str]:
  """Map file extension to file type"""
  extension_map: Dict[str, str] = {
    # Shell scripts
    'sh': 'bash',
    'bash': 'bash',
    'zsh': 'bash',
    'ksh': 'bash',

    # Python files
    'py': 'python',
    'pyw': 'python',
    'pyi': 'python',

    # PHP files
    'php': 'php',
    'php3': 'php',
    'php4': 'php',
    'php5': 'php',
    'php7': 'php',
    'phtml': 'php',

    # HTML files
    'html': 'php',  # HTML is handled by PHP validator
    'htm': 'php',

    # C files
    'c': 'c',
    'h': 'c',

    # Text files
    'txt': 'text',
    'md': 'text',
    'csv': 'text',
    'json': 'text',
    'xml': 'text',
    'yaml': 'text',
    'yml': 'text',
    'ini': 'text',
    'conf': 'text',
    'cfg': 'text',
  }

  return extension_map.get(extension.lower())

def filetype(filename: str) -> str:
  """
  Determine the type of a file based on extension, shebang, and content analysis.

  Args:
    filename: Path to the file to analyze

  Returns:
    str: One of 'bash', 'python', 'php', 'c', 'text', or 'binary'
  """
  # Handle non-existent files
  if not os.path.exists(filename):
    return 'text'  # Default to text for new files

  # Get file extension if present
  extension = Path(filename).suffix.lower().lstrip('.')

  # Check extension first
  if extension:
    if ext_type := get_extension_type(extension):
      return ext_type

  # Check shebang
  if shebang_type := check_shebang(filename):
    return shebang_type

  # Check if binary
  if is_binary_file(filename):
    return 'binary'

  # Check MIME type
  mime_type = get_mime_type(filename)
  if mime_type:
    mime_map = {
      'text/x-shellscript': 'bash',
      'text/x-python': 'python',
      'text/x-php': 'php',
      'text/x-c': 'c',
      'text/html': 'php',  # HTML is handled by PHP validator
    }

    if mime_type in mime_map:
      return mime_map[mime_type]

    if mime_type.startswith('text/'):
      return 'text'

    if not mime_type.startswith('text/'):
      return 'binary'

  # Check file command output
  file_type = get_file_type(filename)
  if 'shell script' in file_type.lower():
    return 'bash'
  if 'python script' in file_type.lower():
    return 'python'
  if 'php script' in file_type.lower():
    return 'php'
  if 'c program' in file_type.lower():
    return 'c'

  # Default to text
  return 'text'

def main():
  """Main entry point when run as a script"""
  if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help'):
    print(__doc__)
    sys.exit(0)

  try:
    print(filetype(sys.argv[1]))
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
  main()

#fin
