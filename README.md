Script    : p
Desc      : Edit/SyntaxCheck/ShellCheck/Execute for
          : bash, php and python scripts.
          : 
          : Bash/php scripts without .sh/.bash/.php extensions are 
          : autodetected from the header.
          : 
          : Uses EDITOR (currently '/usr/local/bin/jj ').
          : 
Synopsis  : p [Options] filename
          : Where 'filename' is the file to edit.
          :
Options   : -f bash|sh|py|html|php|text
          :         File type. If not specified then filetype is
          :         detected. Default text
          : -s      Execute shellcheck after editing.
          : +s      Don't execute shellcheck after editing (default).
          : -l row  Position at row on entry to editor.
          : -t      Append bash template to filename.
          :
Requires  : shellcheck
          : 
