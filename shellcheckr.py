#!/usr/bin/env python3
"""
ShellCheckr: A Python wrapper for shellcheck that provides XML parsing and
pretty printing of shell script analysis results.

Supports multiple shell dialects and configurable severity levels with colorized
output.
"""
import argparse
import subprocess
import shutil
import tempfile
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

try:
    import colorama
    from colorama import Fore, Style
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    # Define dummy color constants if colorama is not available
    class DummyFore:
        RED = YELLOW = BLUE = GREEN = CYAN = MAGENTA = WHITE = ''
    class DummyStyle:
        RESET_ALL = ''
    Fore = DummyFore()
    Style = DummyStyle()

def extract_xml(shell_output: str) -> str:
    """
    Extract XML content from shellcheck output between XML tags.
    """
    start_tag = "<?xml"
    end_tag = "</checkstyle>"
    start_index = shell_output.find(start_tag)
    if start_index == -1:
        raise ValueError("XML start tag not found in the shell output.")
    end_index = shell_output.find(end_tag, start_index)
    if end_index == -1:
        raise ValueError("XML end tag not found in the shell output.")
    end_index += len(end_tag)
    return shell_output[start_index:end_index]

def parse_shellcheck_output(xml_content: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Parse XML content from shellcheck into a structured dictionary of errors.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML content: {e}") from e

    result: Dict[str, List[Dict[str, str]]] = {}
    for file_elem in root.findall('file'):
        file_name = file_elem.get('name')
        if not file_name:
            continue

        errors = [
            {
                'line': err.get('line', ''),
                'column': err.get('column', ''),
                'severity': err.get('severity', ''),
                'message': err.get('message', ''),
                'source': err.get('source', ''),
            }
            for err in file_elem.findall('error')
        ]
        result[file_name] = errors

    return result

def get_first_error_line(parsed_output: Dict[str, List[Dict[str, str]]]) -> int:
    """
    Return the line number of the first error found in parsed shellcheck output.
    """
    line_numbers = [
        int(err['line'])
        for errors in parsed_output.values()
        for err in errors
        if err['line'].isdigit()
    ]
    return min(line_numbers) if line_numbers else 0

def pretty_print_results(parsed_output: Dict[str, List[Dict[str, str]]],
                         file_contents_map: Optional[Dict[str, List[str]]] = None) -> str:
    """
    Display formatted, color-coded shellcheck results to console.
    Optionally shows source lines if file_contents_map is provided, where key=filename,
    value=list of lines from that file.

    Returns:
        A string representation of the results
    """
    if HAS_COLORAMA:
        colorama.init()

    severity_colors = {
        'error': Fore.RED,
        'warning': Fore.YELLOW,
        'info': Fore.BLUE,
        'style': Fore.CYAN
    }

    output_lines = []

    for filename, errors in parsed_output.items():
        if not errors:
            continue

        output_lines.append(f"\n{Fore.GREEN}=== File: {filename} ==={Style.RESET_ALL}")
        output_lines.append(f"{Fore.GREEN}Found {len(errors)} issues{Style.RESET_ALL}\n")

        for error in errors:
            severity = error['severity'].lower()
            color = severity_colors.get(severity, Fore.WHITE)

            output_lines.append(f"{color}[{severity.upper()}]{Style.RESET_ALL} "
                  f"Line {error['line']}, Column {error['column']}")
            output_lines.append(f"└─ {error['message']}")
            output_lines.append(f"   {Fore.BLUE}({error['source']}){Style.RESET_ALL}")

            # If the file contents are known and the line number is valid, show the code line:
            if file_contents_map and filename in file_contents_map and error['line'].isdigit():
                line_number = int(error['line'])
                lines = file_contents_map[filename]
                if 1 <= line_number <= len(lines):
                    code_line = lines[line_number - 1].rstrip('\n')
                    output_lines.append(f"{Fore.MAGENTA}   Code: {code_line}{Style.RESET_ALL}")

            output_lines.append("")  # Blank line for readability

    result = "\n".join(output_lines)
    print(result)
    return result

def is_shell_script(filepath: str) -> bool:
    """
    Check if a file is a shell script based on extension or content.
    """
    # Check extension
    ext = os.path.splitext(filepath)[1].lower().lstrip('.')
    if ext in ('sh', 'bash', 'zsh', 'ksh'):
        return True

    # Check shebang
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#!') and any(shell in first_line for shell in
                                                 ['/sh', '/bash', '/zsh', '/ksh']):
                return True
    except (IOError, UnicodeDecodeError):
        pass

    # Try using 'file' command
    try:
        result = subprocess.run(
            ['file', '--brief', filepath],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.lower()
        if any(term in output for term in ['shell', 'sh ', 'bash', 'zsh', 'ksh']):
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return False

def run_shellcheck(filepath: str,
                   severity: str = "style",
                   shell: str = "bash",
                   output_file: str = '') -> Optional[str]:
    """
    Execute shellcheck on specified shell file and return path to the resulting
    XML file.
    """
    if not Path(filepath).is_file():
        raise FileNotFoundError(f"Shell script not found: {filepath}")

    if not is_shell_script(filepath):
        raise ValueError(f"File {filepath} does not appear to be a shell script")

    if not shutil.which('shellcheck'):
        print("Error: shellcheck not found. Please install shellcheck.")
        return None

    # Create a temporary file for output if none specified
    if not output_file.strip():
        temp_fd, tmp_name = tempfile.mkstemp(suffix='.xml', prefix='shellcheckr_')
        os.close(temp_fd)
    else:
        tmp_name = output_file

    try:
        result = subprocess.run(
            [
                'shellcheck',
                '--format=checkstyle',
                f'--shell={shell}',
                f'--severity={severity}',
                filepath
            ],
            capture_output=True,
            text=True
        )

        with open(tmp_name, 'w', encoding='utf-8') as f:
            f.write(result.stdout)

        return tmp_name
    except Exception as e:
        print(f"Error running shellcheck: {e}")
        if not output_file.strip():
            Path(tmp_name).unlink(missing_ok=True)
        return None

def open_xml(xml_file: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Read and parse an XML file containing shellcheck results.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return {}  # Empty file
            xml_content = extract_xml(content)
        return parse_shellcheck_output(xml_content)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading XML file: {e}")
        return {}

def shellcheckr(file: str,
                severity: str = 'style',
                shell: str = 'bash',
                output_file: str = '') -> Optional[str]:
    """
    Main function to analyze a shell script and display its results.
    Returns a string representation of the results or None on failure.
    """
    # Verify the file is a shell script
    if not is_shell_script(file):
        print(f"Warning: {file} does not appear to be a shell script.")
        return None

    try:
        xml_file = run_shellcheck(file, severity, shell, output_file)
        if not xml_file:
            return None

        # Read the file contents (so we can display the exact line if there's an issue)
        file_contents_map: Dict[str, List[str]] = {}
        if Path(file).is_file():
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    file_contents_map[file] = f.readlines()
            except UnicodeDecodeError:
                # If we can't read the file as text, just skip showing the code lines
                pass

        parsed_output = open_xml(xml_file)

        # If no issues found, return None
        if not parsed_output or not any(errors for errors in parsed_output.values()):
            return None

        result = pretty_print_results(parsed_output, file_contents_map)

        # Clean up temporary file if we created one
        if "shellcheckr_" in xml_file:
            Path(xml_file).unlink(missing_ok=True)

        return result
    except Exception as e:
        print(f"Error in shellcheckr: {e}")
        return None

def main():
    """
    CLI entry point for shellcheck wrapper.
    """
    parser = argparse.ArgumentParser(
        description='Shell script analyzer using shellcheck',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s script.sh
  %(prog)s --severity warning --shell bash script.sh
  %(prog)s -s error -S dash deploy.sh
        """
    )
    parser.add_argument(
        'filepath',
        help='Path to the shell script to analyze'
    )
    parser.add_argument(
        '-s', '--severity',
        choices=['style', 'info', 'warning', 'error'],
        default='style',
        help='Minimum severity of issues to report (default: style)'
    )
    parser.add_argument(
        '-S', '--shell',
        choices=['bash', 'sh', 'dash', 'ksh'],
        default='bash',
        help='Shell dialect to use for analysis (default: bash)'
    )
    parser.add_argument(
        '-o', '--output',
        default='',
        help='File for parsed output.'
    )

    args = parser.parse_args()

    # Verify the file exists
    if not os.path.isfile(args.filepath):
        print(f"Error: File '{args.filepath}' not found.")
        exit(1)

    # Verify it's a shell script
    if not is_shell_script(args.filepath):
        print(f"Error: '{args.filepath}' does not appear to be a shell script.")
        exit(1)

    result = shellcheckr(
        file=args.filepath,
        severity=args.severity,
        shell=args.shell,
        output_file=args.output
    )

    # Exit with status code 1 if any issues exist
    exit(1 if result else 0)

if __name__ == "__main__":
    main()

#fin
