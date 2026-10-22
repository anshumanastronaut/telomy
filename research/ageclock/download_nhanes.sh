#!/bin/bash
cd "$(dirname "$0")/raw"
BASE=https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
STARTYEARS=(2009 2011 2013 2015 2017); SUF=(F G H I J)
FILES=(DEMO CBC BIOPRO GLU GHB HSCRP CRP INS TCHOL HDL TRIGLY)
ok=0; miss=0
for i in "${!STARTYEARS[@]}"; do
  y=${STARTYEARS[$i]}; s=${SUF[$i]}
  for f in "${FILES[@]}"; do
    out="${f}_${s}.xpt"
    code=$(curl -sL -A "$UA" -o "$out" -w "%{http_code}" --max-time 180 "$BASE/$y/DataFiles/${f}_${s}.xpt")
    if [ "$code" = "200" ] && head -c 40 "$out" | grep -q "HEADER RECORD"; then ok=$((ok+1)); echo "OK  ${f}_${s} $(du -h "$out"|cut -f1)"; else rm -f "$out"; miss=$((miss+1)); echo "miss ${f}_${s} ($code)"; fi
  done
done
echo "DONE: $ok ok, $miss missing"; echo "total real XPT: $(ls *.xpt 2>/dev/null|wc -l|tr -d ' ')  size: $(du -sh . | cut -f1)"
