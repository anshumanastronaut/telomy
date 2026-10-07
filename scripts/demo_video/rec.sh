#!/bin/bash
# rec.sh start <chapter> | stop  — records the booted Simulator into $CLIPS/<chapter>.mp4
CLIPS=${CLIPS:-/private/tmp/claude-501/-Users-anshuman-namelix-campaign/900d7cad-d6c4-49a6-83c4-e7617fba3161/scratchpad/video/clips}
mkdir -p "$CLIPS"
if [ "$1" = "start" ]; then
  nohup xcrun simctl io booted recordVideo --codec=h264 --force "$CLIPS/$2.mp4" > /tmp/claude-501/rec.log 2>&1 &
  echo $! > /tmp/claude-501/rec.pid; sleep 1.2; echo "recording $2"
else
  kill -INT "$(cat /tmp/claude-501/rec.pid)"; for i in $(seq 1 20); do kill -0 "$(cat /tmp/claude-501/rec.pid)" 2>/dev/null || break; sleep 0.5; done
  ls -la "$CLIPS" | tail -1
fi
