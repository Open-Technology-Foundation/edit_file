#!/usr/bin/env python
"""
ShellCheckr: A Python wrapper for shellcheck that provides XML parsing and pretty printing of shell script analysis results.

Supports multiple shell dialects and configurable severity levels with colorized output.

"""
import subprocess
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import argparse
import colorama
from colorama import Fore, Style
import random

def extract_xml(shell_output: str) -> str:
  """Extract XML content from shellcheck output between XML tags."""
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
  """Parse XML content from shellcheck into structured dictionary of errors."""
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
  """Return the line number of the first error found in parsed shellcheck output."""
  line_numbers = [int(err['line']) for errors in parsed_output.values() for err in errors if err['line'].isdigit()]
  return min(line_numbers) if line_numbers else 0

def pretty_print_results(parsed_output: Dict[str, List[Dict[str, str]]]) -> None:
  """Display formatted, color-coded shellcheck results to console."""
  colorama.init()
  severity_colors = {
    'error': Fore.RED,
    'warning': Fore.YELLOW,
    'info': Fore.BLUE,
    'style': Fore.CYAN
  }
  for filename, errors in parsed_output.items():
    hdr = True
    for error in errors:
      if hdr:
        print(f"\n{Fore.GREEN}=== File: {filename} ==={Style.RESET_ALL}")
        print(f"{Fore.GREEN}Found {len(errors)} issues{Style.RESET_ALL}\n")
        hdr = False
      severity = error['severity'].lower()
      color = severity_colors.get(severity, Fore.WHITE)
      print(f"{color}[{severity.upper()}]{Style.RESET_ALL} Line {error['line']}, Column {error['column']}")
      print(f"└─ {error['message']}")
      print(f"   {Fore.BLUE}({error['source']}){Style.RESET_ALL}\n")

def run_shellcheck(filepath: str, severity: str = "style", shell: str = "bash", output_file: str = '') -> Optional[str]:
  """Execute shellcheck on specified shell file and return path to XML output."""
  if not Path(filepath).is_file():
    raise FileNotFoundError(f"Shell script not found: {filepath}")
  if not shutil.which('shellcheck'):
    print("Error: shellcheck not found. Please install shellcheck.")
    return None
  output_file = output_file or f'/tmp/shellcheckr_{random.randint(10000, 99999)}.xml'
  try:
    result = subprocess.run([
      'shellcheck',
      '--format=checkstyle',
      f'--shell={shell}',
      f'--severity={severity}',
      filepath
    ], capture_output=True, text=True)

    with open(output_file, 'w', encoding='utf-8') as f:
      f.write(result.stdout)
    return output_file
  except Exception as e:
    print(f"Error running shellcheck: {e}")
    return

def open_xml(xml_file):
  """Read and parse XML file containing shellcheck results."""
  with open(xml_file, 'r', encoding='utf-8') as f:
    xml_content = extract_xml(f.read())
  return parse_shellcheck_output(xml_content)

def shellcheckr(file, severity='style', shell='bash', output_file=''):
  """Main function to analyze shell script and display results."""
  try:
    xml_file = run_shellcheck(file, severity, shell, output_file)
    if xml_file:
      parsed_output = open_xml(xml_file)
      pretty_print_results(parsed_output)
      first_err = get_first_error_line(parsed_output)
      if first_err:
        print(f"First error on line: {first_err}")
      if "shellcheckr_" in xml_file:
        Path(xml_file).unlink(missing_ok=True)
      return parsed_output
    else:
      print("Shellcheck analysis failed")
  except Exception as e:
    print(f"Error: {e}")
  return ''

def main():
  """CLI entry point for shellcheck wrapper."""
  parser = argparse.ArgumentParser(
    description='Shell script analyzer using shellcheck',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  %(prog)s script.sh
  %(prog)s --severity warning --shell bash script.sh
  %(prog)s -s error -sh dash deploy.sh
    """
  )
  parser.add_argument('filepath', help='Path to the shell script to analyze')
  parser.add_argument('-s', '--severity', choices=['style', 'info', 'warning', 'error'], default='style',
                      help='Minimum severity of issues to report (default: style)')
  parser.add_argument('-S', '--shell', choices=['bash', 'sh', 'dash', 'ksh'], default='bash',
                      help='Shell dialect to use for analysis (default: bash)')
  parser.add_argument('-o', '--output', default='', help='File for parsed output.')

  args = parser.parse_args()
  parsed_output = shellcheckr(
    file=args.filepath,
    severity=args.severity,
    shell=args.shell,
    output_file=args.output
  )
  if parsed_output and any(errors for errors in parsed_output.values()):
    exit(1)
  exit(0)

if __name__ == "__main__":
  main()

#fin
