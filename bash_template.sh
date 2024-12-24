#!/usr/bin/env bash
#shellcheck disable=SC1091,SC2155
set -euo pipefail
readonly -- VERSION='1.0.0'
readonly -- PRG0="$(readlink -en -- "$0")"
#shellcheck disable=SC2034
readonly -- PRGDIR="${PRG0%/*}" PRG="${PRG0##*/}"
declare -ix VERBOSE=1 DEBUG=0 DRYRUN=1
#shellcheck disable=SC2015
[ -t 2 ] && declare -- RED=$'\033[0;31m' YELLOW=$'\033[0;33m' GREEN=$'\033[0;32m' NOCOLOR=$'\033[0m' || declare -- RED='' YELLOW='' GREEN='' NOCOLOR=''
vecho() { ((VERBOSE)) || return 0; local msg; for msg in "$@"; do printf '%s: %s\n' "$PRG" "$msg"; done; }
vinfo() { ((VERBOSE)) || return 0; local msg; for msg in "$@"; do >&2 printf '%s: %sinfo%s: %s\n' "$PRG" "$GREEN" "$NOCOLOR" "$msg"; done; }
vwarn() { ((VERBOSE)) || return 0; local msg; for msg in "$@"; do >&2 printf '%s: %swarn%s: %s\n' "$PRG" "$YELLOW" "$NOCOLOR" "$msg"; done; }
vdebug(){ local msg; for msg in "$@"; do >&2 printf '%s: %sdebug%s: %s\n' "$PRG" "$YELLOW" "$NOCOLOR" "$msg"; done; }
error() { local msg; for msg in "$@"; do >&2 printf '%s: %serror%s: %s\n' "$PRG" "$RED" "$NOCOLOR" "$msg"; done; }
die() { local -i exitcode=1; if (($#)); then exitcode=$1; shift; fi; if (($#)); then error "$@"; fi; exit "$exitcode"; }
grep() { /usr/bin/grep "$@"; }
find() { /usr/bin/find "$@"; }
rsync() { /usr/bin/rsync "$@"; }
ssh() { /usr/bin/ssh "$@"; }
scp() { /usr/bin/scp "$@"; }
sed() { /usr/bin/sed "$@"; }
declare -fx grep find rsync ssh scp
noarg() { if (($# < 2)) || [[ ${2:0:1} == '-' ]]; then die 2 "Missing argument for option '$1'"; fi; true; }
decp() { declare -p "$@" | sed 's/^declare -[a-zA-Z-]* //'; }
xcleanup() { local -i exitcode=${1:-0}; [[ -t 0 ]] && printf '\e[?25h'; exit "$exitcode"; }
trap 'xcleanup $?' SIGINT EXIT
# Requires root or sudo
#((EUID)) && { sudo -ln &>/dev/null || die 1 "Requires root, or non-interactive sudo privileges."; exec sudo -n "$0" "$@"; exit 1; }
# Requires host okusi
#[[ $HOSTNAME == 'okusi' ]] || die 1 "Can only run on development host 'okusi'"
#trim() { local v="$*"; v="${v#"${v%%[![:blank:]]*}"}"; echo -n "${v%"${v##*[![:blank:]]}"}"; }
#remblanks() { local str="$1"; while [[ "$str" =~ ([[:space:]]{2,}) ]]; do str="${str//${BASH_REMATCH[1]}/ }"; done; trim "$str"; }
#isodate() { date +'%Y-%m-%d %H:%M:%S'; }
#fqcommand() { local command="$1"; local apt_package="${2:-}"; command -v "$command" &>/dev/null && { command -v "$command"; return 0; }; [[ -z "$apt_package" ]] && die 1 "Command '$command' not found and no package specified"; vinfo "Installing package: $apt_package"; sudo apt-get install -y "$apt_package" >/dev/null 2>&1; command -v "$command" &>/dev/null || die 1 "Failed to install $command"; command -v "$command"; }
# ----------------------------------------------------------------------------------------

usage() {
  local -i exitcode=${1:-0}
  local -- helptext=$(cat <<EOT
$PRG $VERSION - 


Usage:
  $PRG [OPTIONS] 

Options:
	
  -v, --verbose         Increase output verbosity
  -q, --quiet           Suppress non-error messages
												$(decp VERBOSE)
  -V, --version         Print version and exit
												$(decp VERSION)
  -h, --help            Display this help

Examples:
  $PRG 

EOT
)
  ((exitcode)) && >&2 echo "$helptext" || echo "$helptext"
  [[ -z "${1:-}" ]] && return
  exit "$exitcode"
}

#=============================================================================
main() {
  
  #local -a args=()
  while (($#)); do case "$1" in
    #-|--)        noarg "$@"; shift; ?="$1" ;;
    #-|--)        ? ;;
    -h|--help) usage 0;; -v|--verbose) VERBOSE+=1;; -q|--quiet) VERBOSE=0;; -V|--version) echo "$PRG $VERSION"; exit 0;;
    -[hvqV]*) #shellcheck disable=SC2046 #split up single options
                  set -- '' $(printf -- "-%c " $(grep -o . <<<"${1:1}")) "${@:2}";;
    -*)           die 22 "Invalid option '$1'" ;;
    *)            die 2  "Invalid argument '$1'" ;;
                  #args+=( "$1" ) ;;
  esac; shift; done
  
  
  
}

main "$@"
#fin
