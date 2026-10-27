#!/bin/bash
cd "$(dirname "$0")/raw"
BASE=https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# DXA whole-body (DXX) + body measures (BMX) 2011-2018; grip strength (MGX) 2011-2014
STARTYEARS=(2011 2013 2015 2017); SUF=(G H I J)
FILES=(DEMO BMX DXX MGX)
ok=0; miss=0
for i in "${!STARTYEARS[@]}"; do
  y=${STARTYEARS[$i]}; s=${SUF[$i]}
  for f in "${FILES[@]}"; do
    out="${f}_${s}.xpt"
    code=$(curl -sL -A "$UA" -o "$out" -w "%{http_code}" --max-time 180 "$BASE/$y/DataFiles/${f}_${s}.xpt")
    if [ "$code" = "200" ] && head -c 40 "$out" | grep -q "HEADER RECORD"; then ok=$((ok+1)); echo "OK  ${f}_${s} $(du -h "$out"|cut -f1)"; else rm -f "$out"; miss=$((miss+1)); echo "miss ${f}_${s} ($code)"; fi
  done
done
echo "DONE: $ok ok, $miss missing"
