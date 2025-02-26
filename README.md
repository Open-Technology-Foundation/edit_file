# edit_file - Intelligent Text Editor with Validation

Terminal-based text editor wrapper providing safe file editing with built-in validation for multiple file formats. Designed for system administrators and developers who need reliable file editing with syntax checking.

## Features

- 🔍 Comprehensive syntax validation for multiple file formats
- 🛡️ Safe editing with robust temporary file handling
- 🎯 Intelligent editor detection
- 📝 Line number targeting support
- 🔒 Enhanced binary file detection and protection
- 🔄 Advanced path resolution and symlink handling
- ⚡ Smart executable file detection with safety prompts
- 🐚 Improved shellcheck integration (only for shell scripts)
- 🌈 Colorized output with graceful fallback

## Supported File Types

### Programming Languages
- Python (.py, .pyw, .pyi)
- PHP (.php, .phtml, .php3-7)
- Shell Scripts (.sh, .bash, .zsh, .ksh)

### Markup & Data
- JSON/JSONLD (.json, .jsonld)
- YAML (.yml, .yaml)
- XML/XSLT/SVG (.xml, .xsl, .xslt, .svg)
- HTML (.html, .htm, .xhtml)
- Markdown (.md, .markdown, .mdown)
- TOML (.toml, .tml)
- INI/Config (.ini, .conf, .cfg, .config)
- CSV/TSV (.csv, .tsv)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Open-Technology-Foundation/edit_file
cd edit_file
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Make scripts executable:
```bash
chmod +x edit_file.py filetype.py shellcheckr.py
```

4. Optional: Create system-wide symlink:
```bash
sudo ln -s $(pwd)/edit_file.py /usr/local/bin/edit_file
```

## Usage

Basic usage:
```bash
edit_file filename
```

Options:
```bash
edit_file [-n] [-l LINE] [-s] filename

Options:
  -n, --no-validate   Skip validation
  -l, --line LINE     Start editing at specified line number
  -s, --shellcheck    Run shellcheck on shell scripts after editing
```

### Examples

Edit a Python script with validation:
```bash
edit_file script.py
```

Edit YAML file starting at line 50:
```bash
edit_file -l 50 config.yaml
```

Edit shell script with shellcheck:
```bash
edit_file -s deploy.sh
```

Edit without validation:
```bash
edit_file -n data.json
```

## Editor Selection

The script selects editors in this priority:
1. `$EDITOR` environment variable
2. Available system editors in order:
   - joe
   - nano
   - vim
   - vi
   - mcedit
   - ne
   - micro
   - emacs
   - jed
   - gedit

## Dependencies

### Required
- Python 3.12+
- PyYAML
- colorama (optional, for colored output)

### Optional (Enhanced Validation)
- shellcheck (shell script validation)
- yamllint (YAML validation)
- php-cli (PHP validation)
- html5lib (HTML validation)
- mdformat (Markdown validation)
- tomli or toml (TOML validation)

### Installation on Ubuntu

```bash
# Core dependencies
sudo apt install python3-yaml python3-colorama

# Optional validators
sudo apt install shellcheck yamllint php-cli python3-html5lib python3-mdformat python3-tomli
```

## Key Improvements in Latest Version

- ✅ Fixed shellcheck usage: Now only runs on shell scripts
- ✅ Improved error handling: More robust error handling throughout the code
- ✅ Enhanced file type detection: Better detection of file types
- ✅ Better temporary file management: Using Python's tempfile module for safer handling
- ✅ Added colorama fallback: Colorama is now optional with graceful degradation
- ✅ Improved validation: Enhanced validation functions with better error messages
- ✅ Fixed editor preferences
- ✅ Improved code organization: Better structured with clearer function responsibilities

## Project Structure

```
.
├── edit_file.py      # Main editor script
├── filetype.py       # File type detection
├── shellcheckr.py    # Shell script validator
├── requirements.txt  # Python dependencies
└── README.md         # Documentation
```

## Validation Details

The script provides validation for various file types:

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

## Contributing

Contributions welcome! Please feel free to submit pull requests.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

Gary Dean - garydean@yatti.id
