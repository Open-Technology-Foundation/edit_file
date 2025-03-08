# edit_file - Text Editor with Validation

A terminal-based text editor wrapper with built-in validation for multiple file formats. Designed for system administrators and developers who need reliable file editing with syntax checking.

## Features

- Syntax validation for multiple file formats
- Safe file editing with temporary file handling
- Automatic editor detection
- Line number targeting support
- Binary file detection and protection
- Shell script validation with shellcheck

## Supported File Types

- **Code**: Python, PHP, Shell scripts
- **Data**: JSON, YAML, XML, TOML, INI, CSV
- **Markup**: HTML, Markdown, SVG

## Installation

```bash
# Clone the repository
git clone https://github.com/Open-Technology-Foundation/edit_file
cd edit_file
```

### Setup Environment and Dependencies

The tool uses a virtual environment and requires Python packages and external programs for full functionality:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x edit_file edit_file.py filetype.py shellcheckr.py
```

#### External Programs

Some validators require external programs:

```bash
# For Ubuntu/Debian
sudo apt install shellcheck yamllint php-cli

# For Fedora/RHEL/CentOS
sudo dnf install ShellCheck yamllint php-cli

# For macOS with Homebrew
brew install shellcheck yamllint php
```

The tool works without these programs but will skip validation for those file types.

### System-wide Installation (optional)

```bash
# Create a system-wide link to the launcher script
sudo ln -s $(pwd)/edit_file /usr/local/bin/edit_file
```

The launcher script automatically activates the virtual environment before running the Python program.

## Usage

Basic usage:
```bash
./edit_file <filename>
```

Options:
```
-n, --no-validate   Skip validation
-l, --line LINE     Start editing at specified line number
-s, --shellcheck    Run shellcheck on shell scripts
-V, --version       Show version information
```

If installed system-wide, you can use it from any directory:
```bash
edit_file <filename>
```

### Examples

Edit Python file with validation:
```bash
./edit_file script.py
```

Edit YAML file starting at line 50:
```bash
./edit_file -l 50 config.yaml
```

Edit shell script with shellcheck validation:
```bash
./edit_file -s deploy.sh
```

Skip validation when editing:
```bash
./edit_file -n data.json
```

## Editor Selection

The tool selects editors in this priority:
1. `$EDITOR` environment variable
2. Available system editors: joe, nano, vim, vi, mcedit, ne, micro, emacs, jed, gedit

## Validation Methods

| File Type | Validation Method |
|-----------|-------------------|
| Python    | Python compiler   |
| PHP       | php -l            |
| Shell     | bash -n + shellcheck |
| JSON      | json.load         |
| YAML      | yamllint + PyYAML |
| XML       | ElementTree       |
| HTML      | html5lib          |
| Markdown  | mdformat          |
| TOML      | tomli/toml        |
| INI       | configparser      |
| CSV       | csv module        |

## Requirements

### Core
- Python 3.12+
- PyYAML (for YAML validation)

### Optional Python Dependencies
- colorama (for colored output)
- html5lib (for HTML validation)
- mdformat (for Markdown validation)
- tomli (for TOML validation)

### External Tools
- shellcheck (for enhanced shell script validation)
- yamllint (for enhanced YAML validation)
- php-cli (for PHP validation)

## Project Files

- `edit_file.py` - Main editor script
- `filetype.py` - File type detection
- `shellcheckr.py` - Shell script validation wrapper
- `requirements.txt` - Python dependencies

## License

Licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.