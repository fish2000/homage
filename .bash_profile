#!/usr/bin/env bash

# HOMEBREW PACKAGES REQUIRED BY THE SHIT IN THIS FILE:
# • Bash
# • Python, Python@2
# • PyPy, PyPy3
# • Ruby
# • NodeJS
# • Go
# • pkg-config
# • man-db (also recommended: stdman)
# • most
# • dircolors/gdircolors
# • figlet
# • wget
# • Curl
# • Emacs
# • Autogen (for `columns`; see below)
# • Coreutils
# • OSXUtils
# • file-formula
# • PostgreSQL
# • Git
# • git-utils
# • lorem
# • youtube-dl
# • direnv

# HOMEBREW CASKS REQUIRED BY THE SHIT IN THIS FILE:
# • Java
# • MacTeX
# • AnyBar

# PYTHON MODULES REQUIRED BY THE SHIT IN THIS FILE:
# • pythonpy
# • Pygments
# • bpython
# • ipython
# • ptpython
# • httpie

# HISTORY: I have been doomed to repeat it.
export HISTIGNORE="\
&:\
[bf]g:\
exit:\
*>|*:\
*rm*-rf*:\
*brew*cask*home*:\
*brew*home*"                    # keep bad shit out of history
shopt -s histappend             # append history rather than overwrite
shopt -s cmdhist                # one command per line

unset HISTFILESIZE
export HISTSIZE=1000000
export SAVEHIST=999999
export HISTCONTROL=ignoreboth   # ignore dupes AND lines starting with spaces
export HISTTIMEFORMAT='%F %T '  # add the full date and time to lines

# So, LET'S DANCE!!
homedir="/Users/${USER}"
bashconfig="${homedir}/.bash_config.d"
cachedir="${homedir}/.cache"
configdir="${homedir}/.config"
scriptbin="${homedir}/.script-bin"
nodemodules="${cachedir}/npm/lib/node_modules"

localbin="/usr/local/bin"
localopt="/usr/local/opt"

# the path of the righteous man is beset on all sides by evil
MINIMAL_PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/X11/bin"
export ORIGINAL_PATH="${PATH}"
export PATH="\
${localopt}/python/libexec/bin:\
${localopt}/ruby/bin:\
${homedir}/.gem/ruby/2.3.0/bin:\
${localopt}/go/bin:\
${scriptbin}:\
${localbin}:\
/usr/local/sbin:\
/Library/TeX/texbin:\
${MINIMAL_PATH}"

export NODE_PATH="\
${localopt}/node/libexec/lib/node_modules:\
${nodemodules}:\
${NODE_PATH}"

export GOPATH="\
${localopt}/go/libexec:\
${localopt}/go:\
${GOPATH}"

export PKG_CONFIG_PATH="\
${localopt}/python/lib/pkgconfig:\
/usr/local/lib/pkgconfig:\
/opt/X11/lib/pkgconfig:\
${PKG_CONFIG_PATH}"

export EDITOR="${localbin}/emacs"
export PGDATA="/usr/local/var/postgres/ost2"
export XML_CATALOG_FILES="/usr/local/etc/xml/catalog"
export JAVA_HOME=`/usr/libexec/java_home`
export CLICOLOR_FORCE=1 # q.v. `man tree`

gls="${localbin}/gls --color=auto"

alias l="${gls} --ignore=\*.pyc -sF"
alias ll="${gls} --ignore=\*.pyc -lshF"
alias la="${gls} -asF"
alias lla="${gls} -lashF"

alias uman="/usr/bin/man"
alias man="${localbin}/gman"
alias ufile="/usr/bin/file"
alias file="${localopt}/file-formula/bin/file"

function dns () {
    scutil --dns \
        | /usr/bin/egrep -i "{|resolver|domain|reach|}" \
        | /usr/bin/sed -E 's/: ([0-9a-z\.\-]+)$/: \"\1\"/' \
        | pygmentize -l elixir -O "style=monokai"
}

# alias funcs="set | fgrep \" ()\" | fgrep -vi \"virtualenv\" | fgrep -vi \"_git\" | sort"
alias funcs="set | fgrep \" ()\" | fgrep -vi \"virtualenv\" | grep -v \"^_\" | sort"
alias gityo="git addremove . && git commit -m"
alias mateme="mate ${homedir}/.bash_profile"

# alias sufs="${JANGY_PROJECT}/utils/getfilesuffixes.py"
# alias gitwhat="git branch && git status"

alias lipsum="lorem -n 100 | pbcopy"
alias emacs="${localbin}/emacs --no-window-system"
alias siri="say -v Samantha"

function fig () {
    # text="${1:?Text string expected}"
    # -f colossal: use the “colossal” figlet typeface
    # -k: do “kerning” – don’t crash letterforms into one another
    # -w `tput cols`: use the given terminal’s column width
    #                …the figlet command is supposed to be able to
    #                 autodetect this, but it appears not to work
    #                 under the macOS Terminal.app for some reason
    echo "$@" | figlet -f colossal -k -w `tput cols`
}

alias yg="youtube-dl -f mp4 --xattrs --add-metadata"
alias sg="youtube-dl -f mp3 --xattrs --embed-thumbnail --add-metadata"
alias ag="youtube-dl -f mp4 -x --audio-format mp3 --audio-quality 256K --xattrs --embed-thumbnail --add-metadata"

alias time_machine_logs="log stream --style syslog --predicate 'senderImagePath contains[cd] \"TimeMachine\"' --info"
alias serve="open -a /Applications/Safari.app http://localhost:888/ && sudo PYTHONPATH= python3 -m http.server 888"
alias texturetool="/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/texturetool"

# N.B. the `columns` binary is from the Homebrew `autogen` formula:
alias columnize="${localbin}/columns -W `tput cols`"

alias pathvars="python -c '\
from __future__ import print_function;import os;\
[print(var) for var in sorted(os.environ.keys()) if var.endswith(\"PATH\")]\
'"
alias evars="python -c '\
from __future__ import print_function;import os;\
[print(var) for var in sorted(os.environ.keys())]\
' | columnize"

alias syspath="python -c '\
from __future__ import print_function;import sys, site;\
site.removeduppaths();\
print(\":\".join(sys.path).strip(\":\"))\
'"

export BASE_PYTHONPATH="$(syspath)"

# Include private Bash stuff:
bash_private=${bashconfig}/private.bash
if [[ -f $bash_private ]]; then
    source $bash_private
else
    echo "Missing bash support file: ${bash_private}"
fi

# Include URL downloading and filesystem caching Bash funcs:
export URL_DOWNLOAD_CACHE=${cachedir}/bash_url_download
url_dload=${bashconfig}/url_download.sh
url_cache=${bashconfig}/url_cache.sh
if ([[ -f $url_dload ]] && [[ -f $url_cache ]]); then
    source $url_dload
    source $url_cache
else
    echo "Missing bash support:"
    echo "* ${url_dload}"
    echo "* ${url_cache}"
fi

function archive () {
    # Usage:
    # $ archive /tmp/yodogg ~/Dropbox/YoDogg    <-- Archives ~/Dropbox/YoDogg to
    #                                                         /tmp/yodogg.dmg
    dst="${1:?Archive name expected}"
    pth="${2:?Source directory expected}"
    volname="$(basename ${dst^^} | /usr/bin/sed -e s/[^A-Za-z0-9]/-/g)"
    hdiutil create -srcfolder $pth \
        -volname $volname \
        -verbose -ov -nocrossdev -noscrub \
        -format UDBZ "${dst}.dmg"
}

function echopath () {
    # Usage:
    # $ echopath               <-- prints each path in $PATH
    # $ echopath PYTHONPATH    <-- prints each path in $PYTHONPATH
    # … Path elements are printed one per line. They don’t have to
    # be paths, strictly speaking: try e.g. `echopath HISTIGNORE`
    # to see what I am talking about.
    pathvar="${1:-PATH}"
    
    # Check for the variable named in the argument, if any:
    if [[ ! ${!pathvar} ]]; then
        echo "- Path variable ${pathvar} is unknown"
        return 1
    fi
    
    # Split the path into elements delineated by ':' charachters:
    echo "${!pathvar}" | /usr/bin/sed -E 'y/:/\n/'
}

function checkpath () {
    # Usage:
    # $ checkpath                   <-- checks paths in $PATH
    # $ checkpath PYTHONPATH        <-- checks paths in $PYTHONPATH
    # $ export WEIRD_PATH="/yo/dogg;/usr/bin;/var/tmp"
    # $ checkpath WEIRD_PATH ';'    <-- checks paths in $WEIRD_PATH,
    #                                   as delimited by semicolons
    # … Check results are one line per path element, and are labeled
    #   as either valid or void. Path elements are considered valid
    #   if they lead to either an existent directory or an existent
    #   file -- the latter case is not at all uncommonly found in
    #   e.g. Java CLASSPATH jarfile entries, or PYTHONPATH zipfile
    #   and .egg module bundles.
    pathvar="${1:-PATH}"
    IFS="${2:-':'}"
    
    # Check for the named path variable (if any):
    if [[ ! ${!pathvar} ]]; then
        echo "- Path variable “${pathvar}” is unknown"
        return 1
    fi
    
    # Tokenize the path variable, per to what $IFS has been set:
    read -a pathparts <<< "${!pathvar}"
    
    # Confirm that at least one path element is present:
    pathcount=${#pathparts[@]}
    if [[ $pathcount -lt 1 ]]; then
        echo "- Path variable “${pathvar}” contains no path elements"
        return 1
    fi
    
    # Iteratively check and print path elements:
    echo "» Checking path variable “${pathvar}” with ${pathcount} elements…"
    echo ""
    for pth in "${pathparts[@]}"; do
        ([ -d "$pth" ] || [ -f "$pth" ]) && echo "    + valid: ${pth}" || echo "    -  VOID: ${pth}"
    done
    echo ""
}

# Courtesy the UNIX StackExchange:
# https://unix.stackexchange.com/a/124447/57742
function extendpath () {
    # Usage:
    # $ extendpath /yo/dogg/bin
    # $ extendpath /yo/dogg/python-modules PYTHONPATH
    newpath="${1:?New path segment expected}"
    pathvar="${2:-PATH}"
    verbose="${3:-1}"
    
    # Check the existence of the new path:
    if [[ ! -d $newpath ]]; then
        echo "- Directory does not exist: ${newpath}"
        return 1
    fi
    
    # Check for the named path variable, if any:
    if [[ ! ${!pathvar} ]]; then
        echo "- Path variable is unknown: “${pathvar}”"
        return 1
    fi
    
    # Make a nameref pointing to the named variable --
    # q.v. `help declare` sub.
    typeset -n path="${pathvar}"
    case ":${!pathvar}:" in
        *:$newpath:*)  ;;
        *) path="$newpath:${!pathvar}"  ;;
    esac
    
    # Re-export via nameref:
    export path
    
    # Print results if verbose:
    if [[ $verbose -eq 1 ]]; then
        echo "» Path variable “${pathvar}” components:"
        echo ""
        echo "${!pathvar}" | /usr/bin/sed -E 'y/:/\n/'
        echo ""
    fi
}

function python_module_run () {
    # Usage:
    # $ python_module_run python3 bpython  --config=path/to/config ...
    # $ python_module_run python3 IPython  --config=path/to/config ...
    # $ python_module_run python3 ptpython --config-dir=path/to/config-dir ...
    # $ python_module_run python2 bpython  --config=path/to/config.py2 ...
    # … Issuing one of the above commands will first ensure that:
    #  [a] `python3` is an available executable on the current PATH,
    #  [b] `~/.script-bin/repl-bpython.py` is a readable file, and
    #  [c] ${pythonpath} contains '~/.script-bin' and $PWD, as well as
    #       anything from any existing $PYTHONPATH variable
    # … If all of these conditions are met, it will assemble a command:
    # $ PYTHONPATH=$pythonpath $executable -m $module $config -i $replenv $@
    # … using the arguments it was passed and its environment to populate
    #   the variables from which this command is built. Ultimately this will
    #   execute a Python REPL (read-evaluate-print-loop) interpreter that
    #   exposes an interactive Python environment.
    # N.B.: Users will generally not execute `python_module_run` themselves;
    #   see below for examples of functions that set up arguments to a specific
    #  `python_module_run` command and then execute that.
    executable="${1:?Python interpreter expected}"
    modulename="${2:?Python module name expected}"
    configflag="${3:?REPL configuration expected}"
    replenv="${scriptbin}/repl-${modulename,,}.py"
    shift 3 # restore the original $@ argument-set
    if [[ ! -e $executable ]]; then
        executable="$(which ${executable})"
    fi
    if [[ ! -x $executable ]]; then
        echo "» [ERROR] bad Python interpreter: ${executable}"
        return 1
    fi
    if [[ ! -r $replenv ]]; then
        echo "» [ERROR] unknown REPL env setup: ${replenv}"
        return 1
    fi
    if [[ $PYTHONPATH ]]; then
        pythonpath="${PYTHONPATH}"
        extendpath "$(pwd)" pythonpath 0
    else
        pythonpath="$(pwd)"
    fi
    extendpath ${scriptbin} pythonpath 0
    PYTHONPATH=${pythonpath} ${executable} -m ${modulename} \
                                              ${configflag} \
                                           -i ${replenv} $@
}

function bpy3 () {
    pyversion="3"
    pyname="python${pyversion}"
    modname="bpython"
    config="${configdir}/${modname}/config.py${pyversion}"
    python_module_run $pyname $modname --config=${config} $@
}

function bpypy3 () {
    pyversion="3"
    pyname="pypy${pyversion}"
    modname="bpython"
    config="${configdir}/${modname}/config.py${pyversion}"
    python_module_run $pyname $modname --config=${config} $@
}

function bpy2 () {
    pyversion="2"
    pyname="python${pyversion}"
    modname="bpython"
    config="${configdir}/${modname}/config.py${pyversion}"
    python_module_run $pyname $modname --config=${config} $@
}

function bpypy2 () {
    pyversion="2"
    pyname="pypy"
    modname="bpython"
    config="${configdir}/${modname}/config.py${pyversion}"
    python_module_run $pyname $modname --config=${config} $@
}

alias bpy="bpy3"

function ptpy3 () {
    pyversion="3"
    pyname="python${pyversion}"
    modname="ptpython"
    config="${configdir}/${modname}"
    python_module_run $pyname $modname --config-dir=${config} $@
}

function ptpypy3 () {
    pyversion="3"
    pyname="pypy${pyversion}"
    modname="ptpython"
    config="${configdir}/${modname}"
    python_module_run $pyname $modname --config-dir=${config} $@
}

alias ptpy="ptpy3"

function ipy3 () {
    pyversion="3"
    pyname="python${pyversion}"
    modname="IPython"
    config="${configdir}/${modname}/config${pyversion}.py"
    python_module_run $pyname $modname --config=${config} \
                                       --term-title --banner --nosep --no-confirm-exit \
                                       --colors=LightBG --profile=repl${pyversion} $@
}

function ipy2 () {
    pyversion="2"
    pyname="python${pyversion}"
    modname="IPython"
    config="${configdir}/${modname}/config${pyversion}.py"
    python_module_run $pyname $modname --config=${config} \
                                       --term-title --banner --nosep  --no-confirm-exit \
                                       --colors=Neutral --profile=repl${pyversion} $@
}

alias ipy="ipy3"

function gitwat () {
    git grep -e "$@" `git rev-list --all`
}

function repy () {
    # Usage:
    # $ repy numpy      <-- forces a reinstall of numpy, using pip
    if [ "$1" ]; then
        echo "[repy] Reinstalling ${1}…"
        pip install --upgrade --ignore-installed "${1}"
    else
        echo "[repy] No package specified for reinstallation"
    fi
}

function xmlpp () {
    if [ "$1" ]; then
        curl "$1" | xmllint --format -
    fi
}

function glog () {
    git log \
        --pretty=oneline \
        --graph \
        --abbrev-commit \
        --branches \
        --remotes \
        --all \
        --cherry-mark \
        --full-history $@
}

function yo () {
    if [ "$1" ]; then
        echo "» file results for ${1}"
        file "${1}"
        echo "» otool -L results for ${1}"
        otool -L "${1}"
    fi
}

function yoyo () {
    
    upth="${1:?» File path or command name expected}"
    
    if [[ ! -e "${upth}" ]]; then
        # argument is not an existant path,
        # look it up as a command name:
        if [[ -x $(which $upth) ]]; then
            # found a command named by $upth --
            # reassign with the command’s file path:
            echo "» Command: ${upth}"
            upth=$(which $upth)
        fi
    fi
    
    if [[ -e "${upth}" ]]; then
        
        pth=$(realpath "${upth}")
        echo "» Path: ${pth}"
        if [[ "${pth}" != "${upth}" ]]; then
            echo "» From: ${upth}"
        fi
        
        if [[ ! -d "${pth}" ]]; then
            echo ""
            ll "${pth}"
        fi
        
        # echo "» `hfsdata -{k,A,o}` results for ${pth}"
        # echo ""
        ${localopt}/osxutils/bin/hfsdata -k "${pth}"
        ${localopt}/osxutils/bin/hfsdata -A "${pth}"
        ${localopt}/osxutils/bin/hfsdata -o "${pth}"
        
        # hfsmeta="$(${localopt}/osxutils/bin/hfsdata -A $"${pth}")"
        # echo -n "${hfsmeta}" | /usr/bin/sed -n -E 'y/,/\n/'
        # hfsmeta="$(${localopt}/osxutils/bin/hfsdata -o $"${pth}")"
        # # echo -n "${hfsmeta}" | /usr/bin/sed -n -E 'y/,/\n/'
        # echo -n "${hfsmeta}" | /usr/bin/awk 'BEGIN { FS = "([ \t]*|[ \t]+)(,)([ \t]*|[ \t]+)" } \
        #                                            { siz = split($0, vec) } \
        #                                        END { for (idx = 0; idx < siz; idx++) printf("%s\n", vec[idx]) }'
        
        echo ""
        if [[ ! -d "${pth}" ]]; then
            # echo "» file results for ${pth}"
            # echo ""
            filemeta=$(file -z --preserve-date "${pth}")
            shopt -s nocasematch
            if [[ $filemeta =~ (JPEG|TIFF|JFIF|Exif|image) ]]; then
                echo "${filemeta}" | /usr/bin/awk 'BEGIN { FS = "([ \t]*|[ \t]+)(,)([ \t]*|[ \t]+)" } \
                                                         { siz = split($0, vec) } \
                                                     END { for (idx = 0; idx < siz; idx++) printf("%s\n", vec[idx]) }'
            else
                echo "${filemeta}"
            fi
            shopt -u nocasematch
            
            # echo "» otool -L results for ${pth}"
            # echo ""
            otool -L "${pth}"
        fi
    
    else
        # could not find a useable file path based on input:
        echo "» File path or command name expected"
        echo "» Argument passed was “${upth}”"
    
    fi
    
    echo ""
    
}

function see () {
    upth="${1:?» File path or command name expected}"
    
    if [[ ! -e "${upth}" ]]; then
        # argument is not an existant path,
        # look it up as a command name:
        if [[ -x $(which $upth) ]]; then
            # found a command named by $upth --
            # reassign with the command’s file path:
            # echo "» command: ${upth}"
            yoyo "${upth}"
            return 0
        fi
    fi
    
    echo ""
    if [[ ! -d "${upth}" ]]; then
        # it’s not a directory: `more` thar sucker:
        more "${upth}"
    else
        # it’s a directory: list it:
        l "${upth}"
    fi
}

function pyls () {
    if [ "$1" ]; then
        attribute_count=$(py "len(dir(${1}))")
        item_count=$(py "getattr(${1}, '__len__', lambda *a, **k: 0)()")
        what_is_it=$(py "type(${1}).__name__")
        echo -n "> Python ${what_is_it} “${1}” has ${item_count} member sub-items"
        [ "${item_count}" -eq "0" ] && echo "" || echo ":"
        py ${1} | py -x '"+ %s" % x'
        echo -n "> Python ${what_is_it} “${1}” has ${attribute_count} member attributes"
        [ "${attribute_count}" -eq "0" ] && echo "" || echo ":"
        py "sorted(dir(${1}))" | ${localbin}/columns -W `tput cols`
    fi
}

function getlinks () {
    if [ "$1" ]; then
        echo "» Getting links for “${1}”:"
        curl -s "${1}" | BROWSER="/usr/bin/open -a /Applications/Safari.app %s" urlview
    fi
}

function anybar () {
    if [ "$1" ]; then
        port="${2:-1738}"
        echo "» Setting AnyBar at port ${port} to ${1}…"
        echo -n "${1}" | /usr/bin/nc -4u -w0 localhost "${port}"
    else
        echo "- No color provided for AnyBar"
    fi
}

# Virtualenvwrapper: http://www.doughellmann.com/docs/virtualenvwrapper/
export WORKON_HOME="${homedir}/Praxa"
export PIP_RESPECT_VIRTUALENV=true
export VIRTUALENVWRAPPER_PYTHON="${localopt}/python/libexec/bin/python"

# PROMPT.
bash_prompt=${bashconfig}/bash_prompt.sh
if [[ -f $bash_prompt ]]; then
    source $bash_prompt
else
    echo "Missing git support file: ${bash_prompt}"
fi

# COMPLETION.
git_completion=${bashconfig}/git_completion.sh
if [[ -f $git_completion ]]; then
    source $git_completion
else
    echo "Missing git support file: ${git_completion}"
fi

# HOMEBREW.
export HOMEBREW_INSTALL_BADGE=⚗️
export HOMEBREW_VERBOSE=1
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_EDITOR="${localbin}/mate"
export HOMEBREW_CURL="${localbin}/curl"
export HOMEBREW_GIT="${localbin}/git"

# Without this next command, postgres makes things freak out:
ulimit -n 4096

# Allow `more`/`less`/`most` to recognize ANSI colors in I/O:
export MANPAGER="most"
export PAGER="less"
export LESS="-r"

# Homebrew bash completion!
homebrew_completion="$(brew --prefix)/etc/bash_completion"
if [[ -f $homebrew_completion ]]; then
    source $homebrew_completion
else
    echo "Missing Homebrew support file: ${homebrew_completion}"
fi

# q.v. https://help.github.com/articles/telling-git-about-your-gpg-key/
export GPG_TTY=$(tty)

eval "$(gdircolors ~/.dircolors/dircolors.256dark)" # Configure `dircolors` scheme
eval "$(direnv hook bash)"                          # Configure `direnv` Bash hook
