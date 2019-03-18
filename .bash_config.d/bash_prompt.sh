#!/usr/bin/env bash
#
# DESCRIPTION:
#
#   Set the bash prompt according to:
#    * the active virtualenv,
#    * the branch of the current Git repository, and/or
#    * the return value of the previous command
#
# USAGE:
#
#   1. Save this file as ~/.bash_prompt
#   2. Add the following line to the end of your ~/.bashrc or ~/.bash_profile:
#        source ~/.bash_prompt
#
# PROVENANCE:
#
#   Based on work by woods:    https://gist.github.com/31967
#   Based on work by miki725:  https://gist.github.com/miki725/9783474
#   Based on work by fish2000: https://gist.github.com/fish2000/bb6b3ce711d3da904b48163ca80cb7ca
#

# The various escape codes that we can use to color our prompt.
         RED="\[\033[0;31m\]"
   LIGHT_RED="\[\033[1;31m\]"
      YELLOW="\[\033[0;33m\]"
LIGHT_YELLOW="\[\033[1;33m\]"
   GOLDENROD="\[\033[38;5;220m\]"
       GREEN="\[\033[0;32m\]"
 LIGHT_GREEN="\[\033[1;32m\]"
        BLUE="\[\033[0;34m\]"
  LIGHT_BLUE="\[\033[1;34m\]"
      PURPLE="\[\033[0;35m\]"
LIGHT_PURPLE="\[\033[1;35m\]"
        CYAN="\[\033[0;36m\]"
  LIGHT_CYAN="\[\033[1;36m\]"
  LIGHT_GRAY="\[\033[0;37m\]"
       WHITE="\[\033[1;37m\]"
  COLOR_NONE="\[\e[0m\]"

# determine git branch name
function parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'
}

function parse_git_dirty() {
    [[ $(git status 2> /dev/null | tail -n1) != "nothing to commit, working tree clean" ]] && echo " •"
}

# Determine the branch/state information for this git repository.
function set_git_branch() {
    branch=$(parse_git_branch)
    if [[ $branch == "" ]]; then
        BRANCH=""
    else
        BRANCH="[${LIGHT_CYAN}${branch}${COLOR_NONE}${LIGHT_RED}$(parse_git_dirty)${COLOR_NONE}]"
    fi
}

# Return the prompt symbol to use, colorized based on the return value of the
# previous command.
function set_prompt_symbol() {
  if test $1 -eq 0 ; then
      PROMPT_SYMBOL="\$"
  else
      PROMPT_SYMBOL="${LIGHT_RED}\$${COLOR_NONE}"
  fi
}

# Determine active Python virtualenv details.
function set_virtualenv() {
  if test -z "$VIRTUAL_ENV"; then
      PYTHON_VIRTUALENV=""
  else
      PYTHON_VIRTUALENV="«${GOLDENROD}$(basename ${VIRTUAL_ENV})${COLOR_NONE}»:"
  fi
}

# Set the full bash prompt.
function set_bash_prompt() {
    # Set the PROMPT_SYMBOL variable --
    # We do this first so we don't lose the return value of the last command.
    # set_prompt_symbol $?
    
    # Set the PYTHON_VIRTUALENV and BRANCH variables.
    set_virtualenv
    set_git_branch
    
    # Set the bash prompt variable.
    PS1="${PYTHON_VIRTUALENV}\h:\W${BRANCH}\$ "
}

# Tell bash to execute this function just before displaying its prompt.
export PROMPT_COMMAND=set_bash_prompt