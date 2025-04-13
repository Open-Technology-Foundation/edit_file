#!/usr/bin/env bash
#shellcheck disable=SC1091,SC2155
set -eEuo pipefail +o histexpand
shopt -s extglob globstar checkwinsize #-u dotglob nullglob
# Ensure consistent locale and Disable history
export LC_ALL=C HISTFILE=/dev/null HISTSIZE=0

readonly -- VERSION='1.0.0'
readonly -- PRG0="$(readlink -en -- "$0")"
#shellcheck disable=SC2034
readonly -- PRGDIR="${PRG0%/*}" PRG="${PRG0##*/}"

# Message functions for formatting output
declare -ix VERBOSE=1 DEBUG=0 DRYRUN=1
declare -- RED='' YELLOW='' GREEN='' CYAN='' NOCOLOR=''
[ -t 2 ] && { RED=$'\e[31m' YELLOW=$'\e[33m' GREEN=$'\e[32m' CYAN=$'\e[36m' NOCOLOR=$'\e[0m'; }
#shellcheck disable=SC2015
_text() { (($1)) && ((${#3})) && printf '%s%s: %s%s\n' "$2" "$PRG" "$3" "$NOCOLOR" || true; }
text()    {     _text 1        ""         "$*"; }
success() {     _text $VERBOSE "$GREEN"   "$*"; }
info()    { >&2 _text $VERBOSE ""         "$*"; }
warn()    { >&2 _text $VERBOSE "$YELLOW"  "$*"; }
error()   { >&2 _text 1        "$RED"     "$*"; }
debug()   { >&2 _text $DEBUG   "$CYAN"    "$*"; }
die() { error "${2:-}"; exit "${1:-1}"; }

grep() { /usr/bin/grep "$@"; }
find() { /usr/bin/find "$@"; }
rsync() { /usr/bin/rsync "$@"; }
ssh() { /usr/bin/ssh "$@"; }
scp() { /usr/bin/scp "$@"; }
sed() { /usr/bin/sed "$@"; }
declare -fx grep find rsync ssh scp sed

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
#fqcommand() { local command="$1"; local apt_package="${2:-}"; command -v "$command" &>/dev/null && { command -v "$command"; return 0; }; [[ -z "$apt_package" ]] && die 1 "Command '$command' not found and no package specified"; info "Installing package: $apt_package"; sudo apt-get install -y "$apt_package" >/dev/null 2>&1; command -v "$command" &>/dev/null || die 1 "Failed to install $command"; command -v "$command"; }
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
    --)           args+=( "$@" ); break ;;
    -*)           die 22 "Invalid option '$1'" ;;
    *)            die 2  "Invalid argument '$1'" ;;
                  #args+=( "$1" ) ;;
  esac; shift; done
  
  text "123334"
  warn 'a warning'  
  
}

main "$@"
#fin
