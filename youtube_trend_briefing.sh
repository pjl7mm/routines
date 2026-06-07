#!/bin/bash
# Daily YouTube trend briefing for keyword(s).
# Usage: ./youtube_trend_briefing.sh
set -euo pipefail

KEYWORDS=("클로드 코드")
RESULTS_PER_KEYWORD=5

if [ -z "${YOUTUBE_API_KEY:-}" ]; then
  echo "Error: YOUTUBE_API_KEY environment variable is not set." >&2
  exit 1
fi

# 24 hours ago in RFC3339 (UTC), required by YouTube Data API publishedAfter
PUBLISHED_AFTER=$(date -u -d '24 hours ago' +"%Y-%m-%dT%H:%M:%SZ")

echo "================================================================"
echo " YouTube Trend Briefing"
echo " Window: videos published after $PUBLISHED_AFTER (UTC)"
echo " Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "================================================================"

for KEYWORD in "${KEYWORDS[@]}"; do
  echo
  echo "## Keyword: $KEYWORD"
  echo

  ENC_KEYWORD=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$KEYWORD")

  SEARCH_JSON=$(curl -s --max-time 30 \
    "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&order=relevance&maxResults=${RESULTS_PER_KEYWORD}&publishedAfter=${PUBLISHED_AFTER}&q=${ENC_KEYWORD}&key=${YOUTUBE_API_KEY}")

  ERROR_MSG=$(echo "$SEARCH_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',{}).get('message',''))")
  if [ -n "$ERROR_MSG" ]; then
    echo "  [API error] $ERROR_MSG"
    continue
  fi

  VIDEO_IDS=$(echo "$SEARCH_JSON" | python3 -c "
import json,sys
d = json.load(sys.stdin)
ids = [item['id']['videoId'] for item in d.get('items', []) if 'videoId' in item.get('id', {})]
print(','.join(ids))
")

  if [ -z "$VIDEO_IDS" ]; then
    echo "  No videos found in the last 24 hours for this keyword."
    continue
  fi

  STATS_FILE=$(mktemp)
  IDS_FILE=$(mktemp)
  curl -s --max-time 30 \
    "https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id=${VIDEO_IDS}&key=${YOUTUBE_API_KEY}" \
    -o "$STATS_FILE"
  printf '%s' "$VIDEO_IDS" > "$IDS_FILE"

  python3 <<PYEOF
import json

with open("$STATS_FILE", encoding="utf-8") as f:
    data = json.load(f)
items = data.get('items', [])

# preserve search relevance order
with open("$IDS_FILE", encoding="utf-8") as f:
    order = f.read().split(',')
items_by_id = {it['id']: it for it in items}
ordered = [items_by_id[i] for i in order if i in items_by_id]

print(f"  Top {len(ordered)} relevant videos (last 24h):")
print()
for idx, it in enumerate(ordered, 1):
    title = it['snippet']['title']
    channel = it['snippet']['channelTitle']
    views = int(it.get('statistics', {}).get('viewCount', 0))
    print(f"  {idx}. {title}")
    print(f"     Channel: {channel} | Views: {views:,}")
print()

# --- Title pattern analysis ---
import re
patterns = {
    'has_number': 0,
    'is_question': 0,
    'is_comparison': 0,
    'has_brackets_or_emphasis': 0,
    'has_superlative_or_hype': 0,
}
comparison_words = ['vs', 'VS', '대' , '비교', '차이']
question_markers = ['?', '？', '하는법', '하는 법', '왜', '어떻게', '뭐', '무엇']
superlative_words = ['최고', '최강', '완벽', '꿀팁', '필수', '추천', '레전드', '충격']

for it in ordered:
    title = it['snippet']['title']
    if re.search(r'\\d', title):
        patterns['has_number'] += 1
    if any(m in title for m in question_markers):
        patterns['is_question'] += 1
    if any(w in title for w in comparison_words):
        patterns['is_comparison'] += 1
    if re.search(r'[\\[\\]【】()（）]', title):
        patterns['has_brackets_or_emphasis'] += 1
    if any(w in title for w in superlative_words):
        patterns['has_superlative_or_hype'] += 1

print("  Title pattern analysis:")
total = len(ordered) or 1
labels = {
    'has_number': 'Contains a number',
    'is_question': 'Question-style / how-to phrasing',
    'is_comparison': 'Comparison-style (vs/비교/차이)',
    'has_brackets_or_emphasis': 'Uses brackets/emphasis ([], (), 【】)',
    'has_superlative_or_hype': 'Superlative/hype words (최고/꿀팁/추천 etc.)',
}
for key, count in patterns.items():
    print(f"    - {labels[key]}: {count}/{total}")
PYEOF

  rm -f "$STATS_FILE" "$IDS_FILE"
done

echo
echo "================================================================"
echo " End of briefing"
echo "================================================================"
