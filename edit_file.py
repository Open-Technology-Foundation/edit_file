#!/usr/bin/env python3
"""
Terminal-based text file editor with validation support for multiple file formats.
Detects an available editor and provides safe file editing with syntax validation.
"""

import os
import shutil
import subprocess
import sys
import json
import yaml
import tempfile
import signal
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple, Union
import re

try:
    # Optional dependency for progress indication and colored output
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    # Optional dependency for colored output
    import colorama
    from colorama import Fore, Style
    HAS_COLORAMA = True
    colorama.init()
except ImportError:
    HAS_COLORAMA = False
    # Define dummy color constants if colorama is not available
    class DummyFore:
        RED = YELLOW = GREEN = BLUE = CYAN = MAGENTA = WHITE = ''
    class DummyStyle:
        RESET_ALL = BRIGHT = DIM = ''
    Fore = DummyFore()
    Style = DummyStyle()

from filetype import filetype
from shellcheckr import shellcheckr

class EditorNotFoundError(Exception):
  """Raised when no suitable text editor is found"""
  pass

class ValidationError(Exception):
  """
  Raised when file validation fails.
  
  Attributes:
      message (str): Error message
      file_path (str): Path to file that failed validation
      error_type (str): Type of error (syntax, format, etc.)
      line (int, optional): Line number where error occurred
      column (int, optional): Column number where error occurred
  """
  def __init__(self, message, file_path=None, error_type="validation", line=None, column=None):
    self.message = message
    self.file_path = file_path
    self.error_type = error_type
    self.line = line
    self.column = column
    
    # Build full error message with location information
    msg = message
    if file_path:
      msg = f"[{file_path}] {msg}"
    if line is not None:
      location = f"line {line}"
      if column is not None:
        location += f", column {column}"
      msg = f"{msg} at {location}"
        
    super().__init__(msg)
      
  def __str__(self):
    color_start = ""
    color_end = ""
    
    if HAS_COLORAMA:
      # Color code by error type
      if self.error_type == "syntax":
        color_start = Fore.RED + Style.BRIGHT
      elif self.error_type == "format":
        color_start = Fore.YELLOW
      else:
        color_start = Fore.MAGENTA
      color_end = Style.RESET_ALL
      
    return f"{color_start}{super().__str__()}{color_end}"

def touch_with_stats(new_file: Path, reference_file: Path) -> None:
  """Create a new file with the same metadata as a reference file."""
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
      # Read 4096 bytes to match filetype.py's binary detection
      chunk = f.read(4096)
      # Text files shouldn't contain null bytes
      return b'\x00' not in chunk
  except IOError:
    return False

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
  except FileNotFoundError:
    raise ValidationError("PHP interpreter not found. Please install PHP.")

def validate_json(filepath: str) -> bool:
  """Validate JSON file syntax."""
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      content = f.read()
    try:
      json.loads(content)
      return True
    except json.JSONDecodeError as e:
      # Improve error message with line and column information
      line_no = e.lineno
      col_no = e.colno
      # Get the problematic line
      content_lines = content.split('\n')
      error_line = content_lines[line_no-1] if line_no <= len(content_lines) else ""
      # Add ^ indicator pointing to the error position
      pointer = ' ' * (col_no-1) + '^'
      error_msg = f"Invalid JSON at line {line_no}, column {col_no}:\n{error_line}\n{pointer}\nError: {e.msg}"
      raise ValidationError(error_msg)
  except UnicodeDecodeError:
    raise ValidationError("Invalid encoding. JSON files must be UTF-8 encoded.")

def validate_yaml(filepath: str) -> bool:
  """Enhanced YAML validation using yamllint or PyYAML."""
  errors = []

  # Try yamllint first if available
  try:
    result = subprocess.run(
      ['yamllint', '-f', 'parsable', filepath],
      capture_output=True, text=True
    )
    if result.returncode == 0:
      return True
  except (FileNotFoundError, subprocess.SubprocessError) as e:
    errors.append(f"yamllint: {e}")

  # Fall back to PyYAML
  try:
    yaml.safe_load(Path(filepath).read_text(encoding='utf-8'))
    return True
  except yaml.YAMLError as e:
    errors.append(f"PyYAML: {e}")
    raise ValidationError(f"Invalid YAML: {errors[-1]}")
  except UnicodeDecodeError:
    raise ValidationError("Invalid encoding. YAML files must be UTF-8 encoded.")

def validate_xml(filepath: str) -> bool:
  """Validate XML using ElementTree."""
  try:
    import xml.etree.ElementTree as ET
    ET.parse(filepath)
    return True
  except ET.ParseError as e:
    raise ValidationError(f"Invalid XML: {e}")
  except Exception as e:
    raise ValidationError(f"XML validation error: {e}")

def validate_toml(filepath: str) -> bool:
  """Validate TOML file."""
  try:
    import tomli
    with open(filepath, 'rb') as f:
      tomli.load(f)
    return True
  except ImportError:
    try:
      import toml
      with open(filepath, 'r', encoding='utf-8') as f:
        toml.load(f)
      return True
    except ImportError:
      raise ValidationError("Neither tomli nor toml package is installed")
    except toml.TomlDecodeError as e:
      raise ValidationError(f"Invalid TOML: {e}")
  except tomli.TOMLDecodeError as e:
    raise ValidationError(f"Invalid TOML: {e}")
  except UnicodeDecodeError:
    raise ValidationError("Invalid encoding. TOML files must be UTF-8 encoded.")

def validate_ini(filepath: str) -> bool:
  """Validate INI file."""
  try:
    import configparser
    config = configparser.ConfigParser()
    config.read(filepath)
    return True
  except configparser.Error as e:
    raise ValidationError(f"Invalid INI: {e}")
  except UnicodeDecodeError:
    raise ValidationError("Invalid encoding. INI files must be UTF-8 encoded.")

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
  except UnicodeDecodeError:
    raise ValidationError("Invalid encoding. CSV files must be UTF-8 encoded.")

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
  except ImportError:
    # If mdformat isn't available, just check if it's readable text
    try:
      with open(filepath, 'r', encoding='utf-8') as f:
        f.read()
      return True
    except Exception as e:
      raise ValidationError(f"Markdown validation error: {e}")
  except Exception as e:
    raise ValidationError(f"Invalid Markdown: {e}")

def validate_python(filepath: str) -> bool:
  """
  Validate Python syntax by attempting to compile it.
  
  Follows PEP 263 for encoding detection by checking for
  coding declarations in the first two lines of the file.
  """
  try:
    # Default to UTF-8 per PEP 3120
    encoding = 'utf-8'
    
    # Try to detect encoding from the file (PEP 263)
    with open(filepath, 'rb') as f:
      # Check for BOM
      bom = f.read(3)
      if bom == b'\xef\xbb\xbf':
        # UTF-8 with BOM
        encoding = 'utf-8-sig'
      else:
        # No BOM, rewind and check for coding declaration in first two lines
        f.seek(0)
        
        # Per PEP 263, the encoding declaration must be in the first or second line
        # Both lines are read with latin-1 which can decode any byte value
        first_line = f.readline().decode('latin-1', errors='replace')
        second_line = f.readline().decode('latin-1', errors='replace')
        
        # Strict pattern matching per PEP 263
        pattern = r'^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)'
        
        # Check first line
        match = re.search(pattern, first_line)
        if not match:
          # Check second line only if first line is a shebang
          if first_line.startswith('#!'):
            match = re.search(pattern, second_line)
        
        if match:
          declared_encoding = match.group(1)
          try:
            # Verify that it's a valid encoding
            'test'.encode(declared_encoding)
            encoding = declared_encoding
          except LookupError:
            # Invalid encoding specified, fall back to utf-8
            pass
    
    # Now read the file with the correct encoding
    with open(filepath, 'r', encoding=encoding) as f:
      content = f.read()
      
    try:
      compile(content, filepath, 'exec')
      return True
    except SyntaxError as e:
      line = e.lineno
      column = e.offset if hasattr(e, 'offset') else None
      # Get the actual error line from the content
      error_line = None
      if line is not None:
        content_lines = content.split('\n')
        if 0 < line <= len(content_lines):
          error_line = content_lines[line-1]
      
      # Format a helpful error message
      error_msg = f"Invalid Python syntax: {e}"
      if error_line:
        error_msg += f"\n{error_line}"
        if column:
          error_msg += f"\n{' ' * (column-1)}^"
          
      raise ValidationError(
        error_msg, 
        filepath, 
        error_type="syntax", 
        line=line, 
        column=column
      )
  except UnicodeDecodeError:
    # If we failed to decode with detected encoding, try utf-8 as a fallback
    try:
      with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
      compile(content, filepath, 'exec')
      return True
    except UnicodeDecodeError:
      raise ValidationError(
        f"Invalid encoding. Failed to decode with {encoding} or utf-8.", 
        filepath, 
        error_type="format"
      )
    except SyntaxError as e:
      raise ValidationError(
        f"Invalid Python syntax: {e}", 
        filepath, 
        error_type="syntax", 
        line=e.lineno, 
        column=e.offset if hasattr(e, 'offset') else None
      )

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
  except FileNotFoundError:
    raise ValidationError("Bash interpreter not found.")

def validate_html(filepath: str) -> bool:
  """Validate HTML using html5lib."""
  try:
    import html5lib
    with open(filepath, 'r', encoding='utf-8') as f:
      html5lib.parse(f.read())
    return True
  except ImportError:
    # If html5lib isn't available, just check if it's readable text
    try:
      with open(filepath, 'r', encoding='utf-8') as f:
        f.read()
      return True
    except Exception as e:
      raise ValidationError(f"HTML validation error: {e}")
  except Exception as e:
    raise ValidationError(f"Invalid HTML: {e}")

# Cache for validators to avoid rebuilding the dictionary every time
_validators_cache = None

def get_validators() -> Dict[str, Callable[[str], bool]]:
  """
  Return a dictionary of validator functions keyed by short name.
  Also map various extensions to the canonical validator.
  Uses caching for better performance.
  """
  global _validators_cache
  
  # Return cached validators if already built
  if _validators_cache is not None:
    return _validators_cache
    
  base_validators = {
    name.replace('validate_', ''): obj
    for name, obj in globals().items()
    if name.startswith('validate_') and callable(obj)
  }

  # Extension to validator mapping
  extensions = {
    # YAML files
    'yml': base_validators['yaml'],
    'yaml': base_validators['yaml'],

    # INI/Config files
    'conf': base_validators['ini'],
    'cfg': base_validators['ini'],
    'config': base_validators['ini'],
    'ini': base_validators['ini'],

    # HTML files
    'htm': base_validators['html'],
    'html': base_validators['html'],
    'xhtml': base_validators['html'],

    # Shell scripts
    'bash': base_validators['shell'],
    'sh': base_validators['shell'],
    'zsh': base_validators['shell'],
    'ksh': base_validators['shell'],

    # Python files
    'py': base_validators['python'],
    'pyw': base_validators['python'],
    'pyi': base_validators['python'],

    # PHP files
    'php': base_validators['php'],
    'php3': base_validators['php'],
    'php4': base_validators['php'],
    'php5': base_validators['php'],
    'php7': base_validators['php'],
    'phtml': base_validators['php'],
    'phps': base_validators['php'],

    # XML files
    'xml': base_validators['xml'],
    'xsl': base_validators['xml'],
    'xslt': base_validators['xml'],
    'svg': base_validators['xml'],

    # JSON files
    'json': base_validators['json'],
    'jsonld': base_validators['json'],

    # Markdown files
    'md': base_validators['markdown'],
    'markdown': base_validators['markdown'],
    'mdown': base_validators['markdown'],

    # CSV files
    'csv': base_validators['csv'],
    'tsv': base_validators['csv'],

    # TOML files
    'toml': base_validators['toml'],
    'tml': base_validators['toml'],
  }
  
  # Cache the result
  _validators_cache = {**base_validators, **extensions}
  return _validators_cache

# ------------------------------------------------------------------------
# EDITOR DETECTION AND FILE EDITING
# ------------------------------------------------------------------------
def find_editor(editor: str) -> Optional[str]:
  """
  Find editor in PATH and common Linux locations.
  
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
  Find and return path to a suitable text editor.
  
  Checks EDITOR environment variable first, then tries
  preferred editors in order.
  
  Raises:
    EditorNotFoundError: if no suitable editor found
  """
  if (user_editor := os.environ.get('EDITOR', '').strip()):
    if editor_path := find_editor(user_editor):
      return editor_path

  preferred_editors = [
    'joe', 'nano', 'vim', 'vi', 'mcedit', 'ne',
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
  Find full path of executable in PATH.
  
  Args:
    filename: Name of executable
  Returns:
    str: Full path if found, None otherwise
  """
  return shutil.which(filename)

# Import shell script detection from shellcheckr
from shellcheckr import is_shell_script

def edit_file(filename: str,
              *,
              validate: bool = True,
              line_num: int = 0,
              shellcheck: bool = False) -> None:
  """
  Edit file with optional syntax validation.
  
  Args:
    filename: Path to file to edit
    validate: Whether to perform validation (default: True)
    line_num: Line number to jump to on first open
    shellcheck: Whether to run shellcheck on shell scripts
  """
  filepath = Path(filename)

  # Check write permissions before attempting to edit
  if filepath.exists() and not os.access(str(filepath), os.W_OK):
    print(f"Error: No write permission for '{filepath}'", file=sys.stderr)
    sys.exit(1)

  # Check parent directory permissions if creating a new file
  if not filepath.exists() and filepath.parent.exists() and not os.access(str(filepath.parent), os.W_OK):
    print(f"Error: No write permission for directory '{filepath.parent}'", file=sys.stderr)
    sys.exit(1)

  # Create parent directories if they don't exist
  if not filepath.parent.exists():
    try:
      filepath.parent.mkdir(parents=True, exist_ok=True)
      # Verify we can write to the directory after creating it
      if not os.access(str(filepath.parent), os.W_OK):
        print(f"Error: Unable to write to directory '{filepath.parent}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
      print(f"Cannot create parent directory: {e}", file=sys.stderr)
      sys.exit(1)

  # Determine the appropriate validator
  validators_map = get_validators()
  extension = filepath.suffix.lower().lstrip('.')
  validator = validators_map.get(extension) if validate else None

  # If no validator found by extension, try to detect file type
  if validator is None and validate:
    detected_type = filetype(str(filepath))
    if detected_type in validators_map:
      validator = validators_map[detected_type]

  # Get editor path
  try:
    editor_path = get_editor()
  except EditorNotFoundError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

  startline = f"+{line_num}" if line_num > 0 else ""

  try:
    # Create a temporary file for editing in the same directory
    # This helps ensure the temp file is on the same filesystem as the target
    # Use filepath's suffix to preserve file extension for editor syntax highlighting
    extension = filepath.suffix
    with tempfile.NamedTemporaryFile(
      dir=filepath.parent,
      prefix=f".~{filepath.stem}",
      suffix=extension,  # Preserve file extension for proper editor syntax highlighting
      delete=False
    ) as temp_file:
      temp_path = Path(temp_file.name)
      
      # Copy existing file to temp file if it exists, maintaining permissions
      # and metadata, or create an empty file if it doesn't exist
      if filepath.exists():
        # Copy the file with metadata
        shutil.copy2(filepath, temp_path)
        
        # Ensure temporary file has reasonable permissions
        # Get original file mode, but ensure it's at least readable/writable by user
        try:
          original_mode = os.stat(filepath).st_mode
          # Ensure user can read and write the temp file (add 0o600 to existing permissions)
          temp_path.chmod(original_mode | 0o600)
        except (OSError, PermissionError):
          # If we can't get or set permissions, use safe default
          temp_path.chmod(0o644)  # rw-r--r--
      else:
        # Use our utility function to create file with appropriate metadata
        touch_with_stats(temp_path, filepath.parent)
        # Set appropriate permissions for a new file
        temp_path.chmod(0o644)  # rw-r--r--
    
    while True:
      # Prepare editor command
      cmd = [editor_path]
      if startline:
        cmd.append(startline)
        startline = ""  # Only use line number for first edit
      cmd.append(str(temp_path))

      # Provide feedback that editor is being launched
      print(f"{Fore.GREEN}Launching editor: {Fore.CYAN}{os.path.basename(editor_path)}{Style.RESET_ALL}")
      
      # Run the editor with progress indication
      print(f"{Fore.YELLOW}Waiting for editor to close...{Style.RESET_ALL}")
      subprocess.run(cmd, check=True)

      # Skip validation if not requested
      if not validator:
        break

      try:
        # Show validation progress
        filepath_str = str(temp_path)
        print(f"{Fore.BLUE}Validating file: {Style.BRIGHT}{filepath_str}{Style.RESET_ALL}")
        
        if HAS_TQDM:
          # Create visual progress indicator for validation
          with tqdm(total=100, desc="Validating", bar_format='{l_bar}{bar}| {elapsed}s') as pbar:
            # Update progress to 20%
            pbar.update(20)
            time.sleep(0.1)  # Small delay for UX
            
            # Validate the file
            validator(filepath_str)
            
            # Update progress to 80%
            pbar.update(60)
            time.sleep(0.1)  # Small delay for UX
            
            # Run shellcheck if requested
            if shellcheck and is_shell_script(filepath_str) and shutil.which('shellcheck'):
              pbar.set_description("Running shellcheck")
              checks = shellcheckr(filepath_str)
              if checks:
                print(f"\n{Fore.YELLOW}Shellcheck issues:{Style.RESET_ALL}\n{checks}")
              
            # Complete the progress
            pbar.update(20)
        else:
          # No tqdm available, just show text updates
          print("Running syntax validation...")
          validator(filepath_str)
          
          if shellcheck and is_shell_script(filepath_str) and shutil.which('shellcheck'):
            print("Running shellcheck...")
            checks = shellcheckr(filepath_str)
            if checks:
              print(f"\n{Fore.YELLOW}Shellcheck issues:{Style.RESET_ALL}\n{checks}")
        
        print(f"{Fore.GREEN}Validation successful!{Style.RESET_ALL}")
        break
      except ValidationError as val_err:
        print(f"\nValidation failed: {val_err}", file=sys.stderr)
        
        # Consistent prompt format with clear options
        print("\nOptions:")
        print("  [e] - Edit again")
        print("  [s] - Save anyway (not recommended)")
        print("  [q] - Quit without saving")
        
        while True:
          response = input("What would you like to do? [e/s/q]: ").lower().strip()
          if response in ('e', 'edit'):
            # Edit again - break out of this prompt loop and continue the editing loop
            break
          elif response in ('s', 'save'):
            # Save anyway - break out of both loops
            print(f"{Fore.YELLOW}Saving file despite validation errors...{Style.RESET_ALL}")
            # Break the prompt loop and continue to save logic
            break
          elif response in ('q', 'quit'):
            print("Quitting without saving.")
            temp_path.unlink(missing_ok=True)
            sys.exit(0)
          else:
            print("Invalid choice. Please enter 'e', 's', or 'q'.")
        
        # If user chose to edit again, continue the outer editing loop
        if response in ('e', 'edit'):
          continue  # Continue the editing loop
        else:
          # User chose to save anyway, break out of the editing loop
          break  # Save the file and exit editing loop

    # Use atomic file replacement to prevent race conditions
    # This ensures the file is either completely replaced or not at all
    if sys.platform == 'win32':
      # Windows doesn't support atomic renames to existing files
      if filepath.exists():
        filepath.unlink()
      shutil.move(str(temp_path), str(filepath))
    else:
      # On Unix-like systems, rename is atomic
      os.rename(str(temp_path), str(filepath))

  except subprocess.CalledProcessError as e:
    if 'temp_path' in locals():
      temp_path.unlink(missing_ok=True)
    print(f"Editor returned error: {e}", file=sys.stderr)
    sys.exit(1)
  except KeyboardInterrupt:
    if 'temp_path' in locals():
      temp_path.unlink(missing_ok=True)
    print("\nEdit cancelled by user", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    if 'temp_path' in locals():
      temp_path.unlink(missing_ok=True)
    print(f"Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)

# ------------------------------------------------------------------------
# MAIN CLI
# ------------------------------------------------------------------------
def is_valid_path(path: str) -> bool:
  """
  Check if path is valid and free of dangerous patterns.
  
  Args:
    path: Path to validate
  Returns:
    bool: True if path is valid, False otherwise
  """
  # Relative paths with '../' are legitimate and needed for Linux/Unix systems
  # Only reject suspicious shell metacharacters
  if re.search(r'[;&|<>`!]', path):
    return False
    
  # Reject environment variable references in ${VAR} format
  # but allow $ in paths which can be legitimate
  if re.search(r'\$\{[a-zA-Z_][a-zA-Z0-9_]*\}', path):
    return False
    
  # Reject unicode characters that can disguise malicious paths
  if re.search(r'[\u202E\u2066\u2067\u2068\u2069]', path):
    return False
    
  return True

def resolve_path_safely(pathname: str) -> Tuple[Path, Optional[str]]:
  """
  Safely resolve pathname with validation.
  
  Args:
    pathname: Path to resolve
  Returns:
    Tuple[Path, Optional[str]]: (resolved path, error message if any)
  """
  if not is_valid_path(pathname):
    return Path(), "Invalid path: contains suspicious patterns"
    
  try:
    # Resolve path, expanding user directory and environment variables
    expanded_path = os.path.expandvars(os.path.expanduser(pathname))
    return Path(expanded_path).resolve(), None
  except (ValueError, OSError) as e:
    return Path(), f"Path error: {str(e)}"

def main():
  # Handle Ctrl-C without Python tracebacks
  def sigint_handler(signum, frame):
    print("\n", file=sys.stderr)
    sys.exit(1)

  signal.signal(signal.SIGINT, sigint_handler)

  import argparse
  parser = argparse.ArgumentParser(
    description="Edit files with optional validation.",
    formatter_class=argparse.RawDescriptionHelpFormatter
  )
  
  # Help message with examples
  supported_types = sorted(list(get_validators().keys()))
  examples = """
Examples:
  %(prog)s file.py                   # Edit Python file with validation
  %(prog)s -n script.sh              # Edit shell script without validation
  %(prog)s -l 42 config.json         # Edit JSON file starting at line 42
  %(prog)s -s deploy.sh              # Edit shell script and run shellcheck

Supported file types:
  """ + " ".join(supported_types) + """

Environment Variables:
  EDITOR        Text editor to use (defaults to available system editor)

File Type Detection:
  1. Extension-based detection (.py, .sh, .json, etc.)
  2. Shebang detection for scripts (#! lines)
  3. Content analysis for files without extension
"""
  parser.epilog = examples

  parser.add_argument("filename", help="File to edit")
  parser.add_argument("-n", "--no-validate", action="store_true",
    help="Skip validation")
  parser.add_argument("-l", "--line", type=int, default=0,
    help="Start editing at specified line number")
  parser.add_argument("-s", "--shellcheck", action="store_true",
    help="Run shellcheck on shell scripts after editing")
  parser.add_argument("-V", "--version", action="version", version="0.9.0",
    help="Show version information and exit")
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

  args = parser.parse_args()
  incoming_path = args.filename

  # Safely resolve paths with validation
  filename = ""
  if os.path.isfile(incoming_path):
    resolved_path, error = resolve_path_safely(incoming_path)
    if error:
      print(f"Error: {error}", file=sys.stderr)
      sys.exit(1)
    filename = str(resolved_path)
  else:
    if '/' not in incoming_path:
      if exec_path := find_executable(incoming_path):
        resolved_exec, error = resolve_path_safely(exec_path)
        if error:
          print(f"Error: {error}", file=sys.stderr)
          sys.exit(1)
          
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
        resolved_new, error = resolve_path_safely(incoming_path)
        if error:
          print(f"Error: {error}", file=sys.stderr)
          sys.exit(1)
          
        reply = input(f"Create '{resolved_new}'? (y/n) ").strip().lower()
        if reply == 'y':
            filename = str(resolved_new)
        else:
            sys.exit(0)
    else:
      resolved_new, error = resolve_path_safely(incoming_path)
      if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
        
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
