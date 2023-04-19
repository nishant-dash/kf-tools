#!/bin/bash
kf='/snap/bin/kubectl -n kubeflow'
# function for fuzzy finding pods
function kp {
  pattern="${@:-.}"
  #kf get po | grep -iE $pattern | fzf --preview='tail -n 50 {}' --bind shift-up:preview-page-up,shift-down:preview-page-down
  kf get po | grep -iE $pattern | fzf --preview='echo {} | cut -d " " -f1 | xargs kubectl -n kubeflow --tail=100 logs' --bind shift-up:preview-page-up,shift-down:preview-page-down --preview-window wrap
}
# function for viewing logs with specified tool (default uses less)
# example: kpl less, kpl view, kpl less +G, etc...
# Also, can append any command after kpl that operates on a file like grep, sec, etc...
# We save the output to a file because directly calling less/view
# from output of fuzzy finder, breaks the terminal output
function kpl {
  podName="$(echo $(kp) | awk '{print $1}')"
  if [ -z "$podName" ]; then echo No pod specified && return 0; fi
  echo $podName
  viewCmd="${@:-less +G}"
  tempFile=/tmp/temp-log-viewer-$podName.out
  kf logs $podName > $tempFile
  $viewCmd $tempFile
  rm $tempFile
}
# export -f kpl
kpl
