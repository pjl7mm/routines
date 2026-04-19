#!/usr/bin/env python3
"""Daily YouTube trend briefing for interest keywords."""

import os
import re
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta, timezone

KEYWORDS = ["클로드 코드"]
MAX_RESULTS = 5

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _youtube_get(path: str, params: dict) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable is not set")
    params["key"] = api_key
    url = f"{YOUTUBE_API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def search_recent_videos(keyword: str) -> list[dict]:
    published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    search_data = _youtube_get("search", {
        "q": keyword,
        "part": "snippet",
        "type": "video",
        "publishedAfter": published_after,
        "maxResults": MAX_RESULTS,
        "order": "relevance",
    })

    video_ids = [item["id"]["videoId"] for item in search_data.get("items", [])]
    if not video_ids:
        return []

    stats_data = _youtube_get("videos", {
        "part": "statistics,snippet",
        "id": ",".join(video_ids),
    })

    videos = []
    for item in stats_data.get("items", []):
        videos.append({
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "views": int(item["statistics"].get("viewCount", 0)),
            "video_id": item["id"],
        })

    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos[:MAX_RESULTS]


def analyze_title_patterns(titles: list[str]) -> list[str]:
    patterns = []

    number_count = sum(1 for t in titles if re.search(r"\d+", t))
    if number_count:
        patterns.append(f"숫자 포함형 {number_count}개")

    question_count = sum(1 for t in titles if re.search(r"[?？]|방법|어떻게|뭔가|무엇|왜|어디", t))
    if question_count:
        patterns.append(f"질문형 {question_count}개")

    compare_count = sum(1 for t in titles if re.search(r"vs|비교|차이|대비|versus", t, re.IGNORECASE))
    if compare_count:
        patterns.append(f"비교형 {compare_count}개")

    tutorial_count = sum(1 for t in titles if re.search(r"튜토리얼|tutorial|강의|가이드|사용법|입문|시작", t, re.IGNORECASE))
    if tutorial_count:
        patterns.append(f"튜토리얼/가이드형 {tutorial_count}개")

    review_count = sum(1 for t in titles if re.search(r"리뷰|review|후기|사용기|써보니|써봤", t, re.IGNORECASE))
    if review_count:
        patterns.append(f"리뷰/후기형 {review_count}개")

    if not patterns:
        patterns.append("특이 패턴 없음")

    return patterns


def build_message(results: dict[str, list[dict]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"[유튜브 트렌드 브리핑] {now}\n"]

    for keyword, videos in results.items():
        lines.append(f"■ 키워드: {keyword}")
        if not videos:
            lines.append("  최근 24시간 내 영상 없음\n")
            continue

        for i, v in enumerate(videos, 1):
            views = f"{v['views']:,}"
            lines.append(f"  {i}. {v['title']}")
            lines.append(f"     채널: {v['channel']} | 조회수: {views}")

        titles = [v["title"] for v in videos]
        patterns = analyze_title_patterns(titles)
        lines.append(f"  [제목 패턴] {', '.join(patterns)}\n")

    return "\n".join(lines)


def send_telegram(message: str) -> None:
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")
    if not chat_id:
        raise RuntimeError("CHAT_ID environment variable is not set")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    if not body.get("ok"):
        raise RuntimeError(f"Telegram 전송 실패: {body}")


def main():
    results = {}

    for keyword in KEYWORDS:
        print(f"검색 중: {keyword}")
        results[keyword] = search_recent_videos(keyword)

    message = build_message(results)
    print(message)

    send_telegram(message)
    print("Telegram 전송 완료")


if __name__ == "__main__":
    main()
