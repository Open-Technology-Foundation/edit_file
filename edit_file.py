#!/usr/bin/env python3
"""
Terminal-based text file editor with JSON/YAML validation support.
Finds an available editor and provides safe file editing with validation.
"""

import os
import shutil
import subprocess
import sys
import json
import yaml
import tempfile
import signal
from pathlib import Path
from typing import Optional, NoReturn

from filetype import filetype
from shellcheckr import shellcheckr

class EditorNotFoundError(Exception):
  """Raised when no suitable text editor is found"""
  pass

class ValidationError(Exception):
  """Raised when file validation fails"""
  pass

def touch_with_stats(new_file: Path, reference_file: Path) -> None:
  new_file.touch()
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
      chunk = f.read(1024)
      return b'\x00' not in chunk
  except IOError:
    return False

def resolve_path(pathname: str) -> Path:
  """
  Fully resolve a pathname, expanding user directory, environment variables,
  and following all symlinks to get an absolute canonical path.
  """
  expanded_path = os.path.expandvars(os.path.expanduser(pathname))
  return Path(expanded_path).resolve()

# ------------------------------------------------------------------------
# VALIDATORS
# ------------------------------------------------------------------------
def validate_php(filepath: str) -> bool:
  """Validate PHP syntax."""
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
  """Validate JSON file syntax."""
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      json.load(f)
    return True
  except json.JSONDecodeError as e:
    raise ValidationError(f"Invalid JSON: {e}")

def validate_yaml(filepath: str) -> bool:
  """Enhanced YAML validation using yamllint or PyYAML."""
  validators = [
    lambda: subprocess.run(
      ['yamllint', '-f', 'parsable', filepath],
      capture_output=True, text=True, check=True
    ),
    lambda: yaml.safe_load(Path(filepath).read_text(encoding='utf-8')),
  ]
  last_error = None
  for validator in validators:
    try:
      validator()
      return True
    except (FileNotFoundError, subprocess.CalledProcessError, yaml.YAMLError) as e:
      last_error = e
      continue
  raise ValidationError(f"Invalid YAML: {last_error}")

def validate_xml(filepath: str) -> bool:
  """Validate XML using ElementTree."""
  try:
    import xml.etree.ElementTree as ET
    ET.parse(filepath)
    return True
  except ET.ParseError as e:
    raise ValidationError(f"Invalid XML: {e}")

def validate_toml(filepath: str) -> bool:
  """Validate TOML file."""
  try:
    import tomli
    with open(filepath, 'rb') as f:
      tomli.load(f)
    return True
  except tomli.TOMLDecodeError as e:
    raise ValidationError(f"Invalid TOML: {e}")

def validate_ini(filepath: str) -> bool:
  """Validate INI file."""
  try:
    import configparser
    config = configparser.ConfigParser()
    config.read(filepath)
    return True
  except configparser.Error as e:
    raise ValidationError(f"Invalid INI: {e}")

def validate_csv(filepath: str) -> bool:
  """Validate CSV structure."""
  import csv
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      reader = csv.reader(f)
      header = next(reader, None)
      if header is None:  # empty file
        return True
      row_length = len(header)
      for i, row in enumerate(reader, 2):
        if len(row) != row_length:
          raise ValidationError(f"Inconsistent number of columns at line {i}")
    return True
  except csv.Error as e:
    raise ValidationError(f"Invalid CSV: {e}")

def validate_markdown(filepath: str) -> bool:
  """
  Basic Markdown "validation" by reading and handing over to mdformat.
  Approves unless there's a parsing accident.
  """
  try:
    import mdformat
    with open(filepath, 'r', encoding='utf-8') as f:
      content = f.read()
    mdformat.text(content)
    return True
  except Exception as e:
    raise ValidationError(f"Invalid Markdown: {e}")

def validate_python(filepath: str) -> bool:
  """Validate Python syntax by attempting to compile it."""
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      content = f.read()
    compile(content, filepath, 'exec')
    return True
  except SyntaxError as e:
    raise ValidationError(f"Invalid Python syntax: {e}")

def validate_shell(filepath: str) -> bool:
  """Validate shell script syntax using bash -n."""
  try:
    result = subprocess.run(
      ['bash', '-n', filepath],
      capture_output=True,
      text=True
    )
    if result.returncode != 0:
      raise ValidationError(f"Bash syntax check failed:\n{result.stderr}")
    return True
  except subprocess.CalledProcessError as e:
    raise ValidationError(f"Bash validation failed: {e}")

def validate_html(filepath: str) -> bool:
  """Validate HTML using html5lib."""
  try:
    import html5lib
    with open(filepath, 'r', encoding='utf-8') as f:
      html5lib.parse(f.read())
    return True
  except Exception as e:
    raise ValidationError(f"Invalid HTML: {e}")

def get_validators() -> dict:
  """
  Return a dictionary of validator functions keyed by short name.
  Also map various extensions to the canonical validator.
  """
  base_validators = {
    name.replace('validate_', ''): obj
    for name, obj in globals().items()
    if name.startswith('validate_') and callable(obj)
  }
  extensions = {
    'yml': base_validators['yaml'],
    'yaml': base_validators['yaml'],

    'conf': base_validators['ini'],
    'cfg': base_validators['ini'],
    'config': base_validators['ini'],
    'ini': base_validators['ini'],

    'htm': base_validators['html'],
    'html': base_validators['html'],
    'xhtml': base_validators['html'],

    'bash': base_validators['shell'],
    'sh': base_validators['shell'],
    'zsh': base_validators['shell'],
    'ksh': base_validators['shell'],

    'py': base_validators['python'],
    'pyw': base_validators['python'],
    'pyc': base_validators['python'],
    'pyi': base_validators['python'],

    'php': base_validators['php'],
    'php3': base_validators['php'],
    'php4': base_validators['php'],
    'php5': base_validators['php'],
    'php7': base_validators['php'],
    'phtml': base_validators['php'],
    'phps': base_validators['php'],

    'xml': base_validators['xml'],
    'xsl': base_validators['xml'],
    'xslt': base_validators['xml'],
    'svg': base_validators['xml'],

    'json': base_validators['json'],
    'jsonld': base_validators['json'],

    'md': base_validators['markdown'],
    'markdown': base_validators['markdown'],
    'mdown': base_validators['markdown'],

    'csv': base_validators['csv'],
    'tsv': base_validators['csv'],

    'toml': base_validators['toml'],
    'tml': base_validators['toml'],
  }
  return {**base_validators, **extensions}

# ------------------------------------------------------------------------
# EDITOR DETECTION AND FILE EDITING
# ------------------------------------------------------------------------
def find_editor(editor: str) -> Optional[str]:
  """
  Find editor in PATH and in common Linux locations.
  Args:
    editor: Name of editor to find
  Returns:
    str: Full path to editor if found, None otherwise
  """
  if path := shutil.which(editor):
    return path
  common_paths = ['/usr/bin', '/usr/local/bin', '/bin', '/snap/bin']
  for base in common_paths:
    path = os.path.join(base, editor)
    if os.path.isfile(path) and os.access(path, os.X_OK):
      return path
  return None

def get_editor() -> str:
  """
  Find and return the path to a suitable text editor.
  Checks the EDITOR environment variable first, then tries
  preferred editors in order.
  Raises:
    EditorNotFoundError: if no suitable editor is found
  """
  if (user_editor := os.environ.get('EDITOR', '').strip()):
    if editor_path := find_editor(user_editor):
      return editor_path

  preferred_editors = [
    'nano', 'vim', 'vi', 'mcedit', 'joe', 'ne',
    'micro', 'emacs', 'jed', 'gedit'
  ]
  for ed in preferred_editors:
    if (editor_path := find_editor(ed)):
      if 'EDITOR' not in os.environ:
        os.environ['EDITOR'] = ed
      return editor_path

  raise EditorNotFoundError("No suitable text editor found.")

def find_executable(filename: str) -> Optional[str]:
  """
  Find the full path of an executable in PATH. Similar to 'command -v' in bash.
  Args:
    filename: Name of executable
  Returns:
    str: Full path if found, None otherwise
  """
  return shutil.which(filename)

def edit_file(filename: str,
              *,
              validate: bool = True,
              line_num: int = 0,
              shellcheck: bool = False) -> None:
  """
  Edit a file with optional syntax validation for supported file formats.
  Args:
    filename: Path to the file to edit
    validate: Whether to perform validation (default: True)
    line_num: Line number to jump to on first open
    shellcheck: Whether to run shellcheck after editing shell scripts
  """
  filepath = Path(filename)

  if not filepath.parent.exists():
    try:
      filepath.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
      print(f"Cannot create parent directory: {e}", file=sys.stderr)
      sys.exit(1)

  validators_map = get_validators()
  extension = filepath.suffix.lower().lstrip('.')
  validator = validators_map.get(extension) if validate else None

  if validator is None and validate:
    detected_type = filetype(str(filepath))  # e.g. 'bash', 'python', etc.
    if detected_type in validators_map:
      validator = validators_map[detected_type]

  temp_path = filepath.parent / f".~{filepath.name}"

  if filepath.exists():
    shutil.copy2(filepath, temp_path)
  else:
    temp_path.touch(exist_ok=True)

  editor_path = get_editor()
  startline = f"+{line_num}" if line_num > 0 else ""

  try:
    while True:
      cmd = [editor_path]
      if startline:
        cmd.append(startline)
        startline = ""
      cmd.append(str(temp_path))

      subprocess.run(cmd, check=True)

      if not validator:
        break

      try:
        validator(str(temp_path))
        if shellcheck and shutil.which('shellcheck'):
          checks = shellcheckr(str(temp_path))
          if checks:
            print(f"Shellcheck issues:\n{checks}")
        break
      except ValidationError as val_err:
        print(f"\nValidation failed: {val_err}", file=sys.stderr)
        response = input("Re-edit file? (y/n) ").lower()
        if response.startswith('y'):
          continue
        if not input("Save anyway? (y/n) ").lower().startswith('y'):
          temp_path.unlink(missing_ok=True)
          sys.exit(1)
        break

    shutil.move(str(temp_path), str(filepath))

  except subprocess.CalledProcessError as e:
    temp_path.unlink(missing_ok=True)
    print(f"Editor returned error: {e}", file=sys.stderr)
    sys.exit(1)
  except KeyboardInterrupt:
    temp_path.unlink(missing_ok=True)
    print("\nEdit cancelled by user", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    temp_path.unlink(missing_ok=True)
    print(f"Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)

# ------------------------------------------------------------------------
# MAIN CLI
# ------------------------------------------------------------------------
def main():
  # Cleanly handle Ctrl-C so we don't dump Python tracebacks
  def sigint_handler(signum, frame):
    print("\n", file=sys.stderr)
    sys.exit(1)

  signal.signal(signal.SIGINT, sigint_handler)

  import argparse
  parser = argparse.ArgumentParser(
    description="Edit files with optional validation."
  )

  supported_types = sorted(list(get_validators().keys()))
  parser.epilog = "Supported validators for extensions/types:\n  " + " ".join(supported_types)

  parser.add_argument("filename", help="File to edit")
  parser.add_argument("-n", "--no-validate", action="store_true",
    help="Skip validation")
  parser.add_argument("-l", "--line", type=int, default=0,
    help="Start editing at specified line number")
  parser.add_argument("-s", "--shellcheck", action="store_true",
    help="Run shellcheck on shell scripts after editing")

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

  args = parser.parse_args()
  incoming_path = args.filename

  filename = ""
  if os.path.isfile(incoming_path):
    filename = str(resolve_path(incoming_path))
  else:
    if '/' not in incoming_path:
      if exec_path := find_executable(incoming_path):
        resolved_exec = Path(exec_path).resolve()
        if is_text_file(str(resolved_exec)):
          resp = input(f"Edit executable [{resolved_exec}]? (y/n) ").strip().lower()
          if resp == 'y':
            filename = str(resolved_exec)
          else:
            sys.exit(0)
        else:
          print(f"[{resolved_exec}] is a binary file.", file=sys.stderr)
          sys.exit(1)
      else:
        resolved_new = resolve_path(incoming_path)
        reply = input(f"Create '{resolved_new}'? (y/n) ").strip().lower()
        if reply == 'y':
          filename = str(resolved_new)
        else:
          sys.exit(0)
    else:
      resolved_new = resolve_path(incoming_path)
      if not resolved_new.exists():
        reply = input(f"Create '{resolved_new}'? (y/n) ").strip().lower()
        if reply == 'y':
          filename = str(resolved_new)
        else:
          sys.exit(0)
      else:
        filename = str(resolved_new)

  if not filename:
    print("No file selected to edit.", file=sys.stderr)
    sys.exit(1)

  edit_file(
    filename,
    validate=(not args.no_validate),
    line_num=args.line,
    shellcheck=args.shellcheck
  )

if __name__ == '__main__':
  main()

#fin
