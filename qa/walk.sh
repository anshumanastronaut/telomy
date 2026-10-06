#!/bin/zsh
# Deep-link to every screen in Expo Go, screenshot each, then build contact sheets.
ROUTES=( "" "vault" "vault?tab=insights" "vault?tab=signals" "vault?tab=timeline" "vault?tab=reports" "sinc" "sessions" "profile"
  "longevity" "risks" "notes" "browse" "browse?name=Heart" "activity" "notifications" "meds" "nutrition" "pins"
  "marker/apob" "marker/cac" "marker/vo2max_lab" "marker/apoe" "marker/liver_pdff" "signal/hrv" "signal/deep_sleep" "domain/cardiovascular"
  "report/2" "menu" "studies" "marketplace" "consent" "family" "care" "brief" "completeness" "research" "memory" "emergency"
  "imaging" "queue" "goals" "log" "upload" "breathe" "onboarding" )
OUT=${0:a:h}/shots
rm -f $OUT/*.png
i=0
for r in $ROUTES; do
  i=$((i+1)); n=$(printf "%02d" $i)
  xcrun simctl openurl booted "exp://127.0.0.1:8081/--/$r"
  sleep 3
  xcrun simctl io booted screenshot "$OUT/${n}_${r//[\/?=]/_}.png" >/dev/null 2>&1
done
echo done $i
