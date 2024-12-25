# edit_file - Smart Text Editor with Validation 

A sophisticated terminal-based text editor wrapper that provides safe file editing with built-in validation for multiple file formats. Perfect for system administrators and developers who need reliable file editing with syntax checking.

## Features

- 🔍 Automatic syntax validation for multiple file formats
- 🔒 Safe editing using temporary files
- 🎯 Smart editor detection and fallback
- 📝 Support for line number targeting
- 🛡️ Binary file protection
- 🔄 Path resolution and symlink handling
- ⚡ Executable file detection and safety prompts

## Supported File Formats

- JSON/JSONLD
- YAML/YML
- XML/XSLT/SVG
- TOML
- INI/Config files
- CSV/TSV
- Markdown
- Python
- Shell scripts (with shellcheck integration)
- PHP
- HTML/XHTML

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/edit_file.git
cd edit_file
```

2. Make the script executable:
```bash
chmod +x edit_file.py
```

3. Optional: Create symlinks for easier access:
```bash
sudo ln -s edit_file.py /usr/local/bin/edit_file
```

## Usage

Basic usage:
```bash
edit_file filename
```

With options:
```bash
edit_file [-n] [-l LINE] filename
```

### Command Line Options

- `-n, --no-validate`: Skip validation
- `-l, --line LINE`: Start editing at specified line number
- `-h, --help`: Show help message

### Examples

Edit a Python file with validation:
```bash
edit_file script.py
```

Edit starting at line 50:
```bash
edit_file -l 50 config.yaml
```

Edit without validation:
```bash
edit_file -n data.json
```

## Editor Selection

The script will use editors in the following order:
1. Value of `$EDITOR` environment variable
2. Available system editors: nano, vim, vi, mcedit, joe, ne, micro, emacs, jed, gedit

## Dependencies

### Required
- Bash
- Python 3.8+
- Standard Python libraries

### Optional (for enhanced validation)
- shellcheck (for shell script validation)
- yamllint (for YAML validation)
- php-cli (for PHP validation)
- html5lib (for HTML validation)
- tomli (for TOML validation)

## Installation of Optional Dependencies

On Ubuntu/Debian:
```bash
sudo apt install shellcheck yamllint php-cli python3-html5lib python3-tomli
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL3 License - see the LICENSE file for details.

## Author

Gary Dean - garydean@yatti.id

