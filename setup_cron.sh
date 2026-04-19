#!/bin/bash
# Set up daily cron job to run youtube_briefing.py every morning at 8:00 AM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(which python3)"
LOG_FILE="$SCRIPT_DIR/briefing.log"

CRON_LINE="0 8 * * * YOUTUBE_API_KEY=\"$YOUTUBE_API_KEY\" $PYTHON $SCRIPT_DIR/youtube_briefing.py >> $LOG_FILE 2>&1"

# Install dependencies if needed
if ! python3 -c "import googleapiclient" 2>/dev/null; then
    pip3 install --quiet google-api-python-client
fi

# Add cron job (skip if already exists)
( crontab -l 2>/dev/null | grep -v "youtube_briefing.py"; echo "$CRON_LINE" ) | crontab -

echo "크론 작업 등록 완료: 매일 오전 8시 실행"
echo "로그 파일: $LOG_FILE"
crontab -l | grep youtube_briefing
