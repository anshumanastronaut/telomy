#!/bin/bash
cd "$(dirname "$0")/raw"
B="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"; UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
# dietary intake (DR1TOT), 25-OH vitamin D (VID), ferritin (FERTIN), folate/B12 (FOLATE), demographics
FILES="2015/DataFiles/DR1TOT_I 2015/DataFiles/VID_I 2015/DataFiles/FERTIN_I 2015/DataFiles/FOLATE_I 2015/DataFiles/DEMO_I \
2017/DataFiles/DR1TOT_J 2017/DataFiles/VID_J 2017/DataFiles/FERTIN_J 2017/DataFiles/FOLATE_J 2017/DataFiles/DEMO_J \
2013/DataFiles/DR1TOT_H 2013/DataFiles/VID_H 2013/DataFiles/VITB12_H 2013/DataFiles/DEMO_H"
ok=0
for f in $FILES; do
  out=$(basename "$f").xpt
  code=$(curl -sL -A "$UA" -o "$out" -w "%{http_code}" --max-time 180 "$B/${f}.xpt")
  if [ "$code" = "200" ] && head -c 40 "$out" | grep -q "HEADER RECORD"; then ok=$((ok+1)); echo "OK $(basename $f) $(du -h $out|cut -f1)"; else rm -f "$out"; echo "miss $(basename $f) ($code)"; fi
done
echo "DONE $ok files"
