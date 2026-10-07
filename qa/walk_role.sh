#!/bin/zsh
# usage: walk_role.sh PREFIX route1 route2 ...
OUT=${0:a:h}/shots; PRE=$1; shift; i=0
for r in "$@"; do i=$((i+1)); n=$(printf "%02d" $i)
  xcrun simctl openurl booted "exp://127.0.0.1:8081/--/$r"; sleep 3
  xcrun simctl io booted screenshot "$OUT/${PRE}_${n}_${r//[\/?=&]/_}.png" >/dev/null 2>&1
done; echo done $i
