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
from typing import Optional

def get_mime_type(filename: str) -> str:
  """Get MIME type of file using 'file' command"""
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

def filetype(filename: str) -> str:
  """
  Determine the type of a file based on extension, shebang, and content analysis.
  
  Args:
    filename: Path to the file to analyze
    
  Returns:
    str: One of 'bash', 'python', 'php', 'c', 'text', or 'binary'
  """
  # Get file extension if present
  extension = Path(filename).suffix.lower().lstrip('.')
  
  # Check extension first
  if extension:
    extension_types = {
      'bash': ['bash', 'sh'],
      'py': ['python'],
      'php': ['php', 'html'],
      'c': ['c'],
      'text': ['txt', 'text']
    }
    
    for ftype, exts in extension_types.items():
      if extension in exts:
        return ftype
        
  # If file doesn't exist and no recognized extension, assume text
  if not os.path.isfile(filename):
    return 'text'
    
  # Check shebang
  if shebang_type := check_shebang(filename):
    return shebang_type
    
  # Check MIME type
  mime_type = get_mime_type(filename)
  if mime_type:
    mime_map = {
      'text/x-shellscript': 'bash',
      'text/x-python': 'python',
      'text/x-php': 'php',
      'text/x-c': 'c'
    }
    
    if mime_type in mime_map:
      return mime_map[mime_type]
    
    if mime_type.startswith('text/'):
      return 'text'
      
  # Check if binary
  file_type = get_file_type(filename)
  binary_signatures = ('ELF', 'PE32', 'Mach-O', 'data', 'binary')
  binary_mime_prefixes = ('application/', 'image/', 'audio/', 'video/')
  
  if (any(sig in file_type for sig in binary_signatures) or
      any(mime_type.startswith(prefix) for prefix in binary_mime_prefixes)):
    return 'binary'
    
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
