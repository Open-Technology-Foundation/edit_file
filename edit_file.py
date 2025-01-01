#!/usr/bin/env python3
"""
Terminal-based text file editor with JSON/YAML validation support.
Finds available editor and provides safe file editing with validation.
"""

import os
import shutil
import subprocess
import sys
import json
import yaml
import tempfile
from pathlib import Path
from typing import Optional, NoReturn

from filetype import filetype
from shellcheckr import shellcheckr

def touch_with_stats(new_file, reference_file):
  Path(new_file).touch()
  shutil.copystat(reference_file, new_file)

def is_text_file(filepath: str) -> bool:
  """
  Check if file is a text file.
  Args:
    filepath: Path to file to check
  Returns:
    bool: True if text file, False if binary
  """
  try:
    with open(filepath, 'rb') as f:
      # Read first 1024 bytes
      chunk = f.read(1024)
      # Check for null bytes which indicate binary
      return b'\x00' not in chunk
  except IOError:
    return False

def resolve_path(pathname):
  """
  Fully resolve a pathname, expanding user directory, environment variables,
  and following all symlinks to get absolute canonical path
  """
  # First expand any environment variables and user directory
  expanded_path = os.path.expandvars(os.path.expanduser(pathname))
  # Use pathlib to resolve the absolute path and follow symlinks
  resolved_path = Path(expanded_path).resolve()
  return str(resolved_path)

class EditorNotFoundError(Exception):
  """Raised when no suitable text editor is found"""
  pass

# VALIDATIONS ===================================
def get_validators() -> dict:
  """
  Return dictionary of validator functions
  Returns:
    dict: Format {'name': validate_name}
  Example:
    {'json': validate_json, 'yaml': validate_yaml, ...}
  """
  base_validators = {
    name.replace('validate_', ''): obj
    for name, obj in globals().items()
    if name.startswith('validate_') and callable(obj)
  }
  # Add common extension variants
  extensions = {
    # YAML variants
    'yml': base_validators['yaml'],
    'yaml': base_validators['yaml'],
    # Config variants
    'conf': base_validators['ini'],
    'cfg': base_validators['ini'],
    'config': base_validators['ini'],
    'ini': base_validators['ini'],
    # HTML variants
    'htm': base_validators['html'],
    'html': base_validators['html'],
    'xhtml': base_validators['html'],
    # Shell script variants
    'bash': base_validators['shell'],
    'sh': base_validators['shell'],
    'zsh': base_validators['shell'],
    'ksh': base_validators['shell'],
    # Python variants
    'py': base_validators['python'],
    'pyw': base_validators['python'],
    'pyc': base_validators['python'],
    'pyi': base_validators['python'],
    # PHP variants
    'php': base_validators['php'],
    'php3': base_validators['php'],
    'php4': base_validators['php'],
    'php5': base_validators['php'],
    'php7': base_validators['php'],
    'phtml': base_validators['php'],
    'phps': base_validators['php'],
    # XML variants
    'xml': base_validators['xml'],
    'xsl': base_validators['xml'],
    'xslt': base_validators['xml'],
    'svg': base_validators['xml'],
    # JSON variants
    'json': base_validators['json'],
    'jsonld': base_validators['json'],
    # Markdown variants
    'md': base_validators['markdown'],
    'markdown': base_validators['markdown'],
    'mdown': base_validators['markdown'],
    # CSV variants
    'csv': base_validators['csv'],
    'tsv': base_validators['csv'],
    # TOML variants
    'toml': base_validators['toml'],
    'tml': base_validators['toml']
  }
  return {**base_validators, **extensions}

class ValidationError(Exception):
  """Raised when file validation fails"""
  pass

def validate_php(filepath: str) -> bool:
  """Validate PHP syntax"""
  try:
    result = subprocess.run(
      ['php', '-l', filepath],
      capture_output=True,
      text=True
    )
    if result.returncode != 0:
      raise ValidationError(f"Invalid PHP syntax:\n{result.stderr}")
    return True
  except subprocess.CalledProcessError as e:
    raise ValidationError(f"PHP validation failed: {e}")

def validate_json(filepath: str) -> bool:
  """
  Validate JSON file syntax.
  Args:
    filepath: Path to JSON file
  Returns:
    bool: True if valid
  Raises:
    ValidationError: If JSON is invalid
  """
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      json.load(f)
    return True
  except json.JSONDecodeError as e:
    raise ValidationError(f"Invalid JSON: {e}")

def validate_yaml(filepath: str) -> bool:
  """Enhanced YAML validation with multiple fallbacks"""
  validators = [
    # Try yamllint first
    lambda: subprocess.run(
        ['yamllint', '-f', 'parsable', filepath],
        capture_output=True, text=True, check=True
    ),
    # Try PyYAML if yamllint not available
    lambda: yaml.safe_load(Path(filepath).read_text(encoding='utf-8')),
    # Could add more validators here
  ]
  for validator in validators:
    try:
      validator()
      return True
    except (FileNotFoundError, subprocess.CalledProcessError,
          yaml.YAMLError) as e:
      last_error = e
      continue
  raise ValidationError(f"Invalid YAML: {last_error}")

def validate_xml(filepath: str) -> bool:
  """Validate XML using ElementTree"""
  try:
    import xml.etree.ElementTree as ET
    tree = ET.parse(filepath)
    return True
  except ET.ParseError as e:
    raise ValidationError(f"Invalid XML: {e}")

def validate_toml(filepath: str) -> bool:
  """Validate TOML file"""
  try:
    import tomli  # for Python < 3.11
    # import tomllib  # for Python >= 3.11
    with open(filepath, 'rb') as f:
      tomli.load(f)
    return True
  except tomli.TOMLDecodeError as e:
    raise ValidationError(f"Invalid TOML: {e}")

def validate_ini(filepath: str) -> bool:
  """Validate INI file"""
  try:
    import configparser
    config = configparser.ConfigParser()
    config.read(filepath)
    return True
  except configparser.Error as e:
    raise ValidationError(f"Invalid INI: {e}")

def validate_csv(filepath: str) -> bool:
  """Validate CSV structure"""
  import csv
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      reader = csv.reader(f)
      header = next(reader)  # Read header
      row_length = len(header)
      for i, row in enumerate(reader, 2):
        if len(row) != row_length:
          raise ValidationError(
            f"Inconsistent number of columns at line {i}"
          )
    return True
  except csv.Error as e:
    raise ValidationError(f"Invalid CSV: {e}")

def validate_markdown(filepath: str) -> bool:
  return True ## not yet implemented (what's there to implement??)
  """Validate Markdown formatting"""
  try:
    import mdformat
    with open(filepath, 'r', encoding='utf-8') as f:
      content = f.read()
    mdformat.text(content)
    return True
  except Exception as e:
    raise ValidationError(f"Invalid Markdown: {e}")

def validate_python(filepath: str) -> bool:
  """Validate Python syntax"""
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      content = f.read()
    compile(content, filepath, 'exec')
    return True
  except SyntaxError as e:
    raise ValidationError(f"Invalid Python syntax: {e}")

def validate_shell(filepath: str) -> bool:
  """Validate shell script syntax using bash -n and shellcheck"""
  errors = []
  # First check basic syntax with bash -n
  try:
    result = subprocess.run(
      ['bash', '-n', filepath],
      capture_output=True,
      text=True
    )
    if result.returncode != 0:
      errors.append(f"Bash syntax check failed:\n{result.stderr}")
      return False
  except subprocess.CalledProcessError as e:
    errors.append(f"Bash validation failed: {e}")
    return False

  if errors:
    raise ValidationError("\n".join(errors))
  return True

def validate_html(filepath: str) -> bool:
  """Validate HTML using html5lib"""
  try:
    import html5lib
    with open(filepath, 'r', encoding='utf-8') as f:
      html5lib.parse(f.read())
    return True
  except Exception as e:
    raise ValidationError(f"Invalid HTML: {e}")


# EDITOR =============================================================
def find_editor(editor: str) -> Optional[str]:
  """
  Find editor in PATH and common Linux locations.
  Args:
    editor: Name of editor to find
  Returns:
    str: Full path to editor if found, None otherwise
  """
  # First check in PATH
  if path := shutil.which(editor):
    return path
  # Check common Ubuntu/Linux locations
  common_paths = [ '/usr/bin', '/usr/local/bin', '/bin', '/snap/bin' ]
  for base in common_paths:
    path = os.path.join(base, editor)
    if os.path.isfile(path) and os.access(path, os.X_OK):
      return path
  return None

def get_editor() -> str:
  """
  Find and return the path to a suitable text editor.
  Sets EDITOR environment variable if not already set.
  Returns:
    str: Path to the selected text editor
  Raises:
    EditorNotFoundError: If no suitable editor is found
  """
  # First check existing EDITOR environment variable
  if editor := os.environ.get('EDITOR', '').strip():
    if editor_path := find_editor(editor):
      return editor_path
  # Check preferred editors in order
  preferred_editors = [
    'nano',        # Common default on Ubuntu
    'vim',         # Very common
    'vi',          # Always present on Unix systems
    'mcedit',      # Midnight Commander editor
    'joe',         # Joe's Own Editor
    'ne',          # Nice Editor
    'micro',       # Modern terminal editor
    'emacs',       # GNU Emacs terminal version
    'jed',         # JED editor
    'gedit'        # GNOME editor (if X11 available)
  ]
  for editor in preferred_editors:
    if editor_path := find_editor(editor):
      # Set EDITOR environment variable if not already set
      if 'EDITOR' not in os.environ:
        os.environ['EDITOR'] = editor
      return editor_path
  raise EditorNotFoundError(
    "No suitable text editor found."
  )

def edit_file(filename: str, *, validate: bool = True, line_num: Optional[int] = 0, shellcheck: Optional[bool] = False) -> None:
  """
  Edit a file with optional syntax validation for supported file formats.
  Args:
    filename: Path to the file to edit
    validate: Whether to perform validation (default: True)
  """
  filepath = Path(filename)
  suffix = filepath.suffix
  stem = filepath.stem

  # Get available validators
  validators = get_validators()
  # Use validator if available for this file type
  validator = validators.get(suffix.lower().lstrip('.')) if validate else None
  if validator is None:
    validator = filetype(filepath)
    if validator:
      validator = validators.get(validator) if validate else None

  try:
    # EDIT
    temp_path = f"{filepath.parent.absolute()}/.~{filepath.name}"
    if filepath.exists():
      shutil.copy2(filepath, temp_path)
    else:
      Path(temp_path).touch(exist_ok=True)

    editor_path = get_editor()
    startline = f"+{line_num}" if line_num > 0 else ''
    while True:
      cmd = [editor_path]
      if startline:
        cmd.append(startline)
        startline = None
      cmd.append(temp_path)
      # execute EDITOR
      subprocess.run(cmd, check=True)
      # Skip validation if disabled or file type not supported
      if not validator or not validate:
        break
      try:
        validator(temp_path)
        if shellcheck:
          if shutil.which('shellcheck'):
            result = shellcheckr(filepath)
            if result:
              print(f"Shellcheck issues:\n{result}")
        break  # Break if validation succeeds
      except ValidationError as e:
        print(f"\nValidation failed: {e}", file=sys.stderr)
        if input("Re-edit file? y/n ").lower().startswith('y'):
          continue
        if not input("Save anyway? y/n ").lower().startswith('y'):
          temp_path.unlink(missing_ok=True)
          sys.exit(1)
        break # save it anyway

    shutil.move(temp_path, filepath)

  except (subprocess.CalledProcessError, KeyboardInterrupt, Exception) as e:
    temp_path.unlink(missing_ok=True)
    error_msg = {
      subprocess.CalledProcessError: f"Editor returned error: {e}",
      KeyboardInterrupt: "\nEdit cancelled by user",
      Exception: f"Unexpected error: {e}"
    }.get(type(e), str(e))
    print(error_msg, file=sys.stderr)
    sys.exit(1)

def find_executable(filename: str) -> Optional[str]:
    """
    Find the full path of an executable in PATH.
    Similar to 'command -v' in bash.
    Args:
        filename: Name of executable to find
    Returns:
        str: Full path if found, None otherwise
    """
    return shutil.which(filename)

if __name__ == '__main__':
  import argparse

  ftype = f"Supported file types:\n"
  for ext in get_validators().keys():
      ftype += f" {ext}"
  parser = argparse.ArgumentParser(description=f"Edit files with optional validation.  \n\n{ftype}")
  parser.add_argument("filename", help="File to edit")
  parser.add_argument("-n", "--no-validate", action="store_true",
                   help="Skip validation")
  parser.add_argument("-l", "--line", type=int, default=0,
                   help="Start editing at specified line number")
  parser.add_argument("-s", "--shellcheck", action="store_true",
                   help="Shellcheck flag")

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

  args = parser.parse_args()

  file_path = args.filename
  filename = ''
  while True:
    # If file exist
    if os.path.isfile(file_path):
      filename = os.path.realpath(file_path)
      break

    # If path doesn't contain '/', treat as possible executable
    # check if it's an executable in the path
    if '/' not in file_path:
      file_path = resolve_path(args.filename)
      # Try to find executable in PATH
      if exec_path := find_executable(os.path.basename(file_path)):
        filename = os.path.realpath(exec_path)
        if filename:
          # Check if it's a text file
          if not is_text_file(filename):
            raise SystemExit(f"[{filename}] is a binary file.")
          # Prompt user
          response = input(f"Edit executable [{filename}]? y/n ").lower()
          if response != 'y':
            raise SystemExit(0)
          break

      # file does not exist
      filename = os.path.realpath(args.filename)
      response = input(f"Create '{filename}'? y/n ").lower()
      if response != 'y':
        raise SystemExit(0)
      break

  edit_file(filename, \
    validate=not args.no_validate, \
    line_num=args.line,
    shellcheck=args.shellcheck)

#fin
