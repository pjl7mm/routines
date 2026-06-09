#!/usr/bin/env python3
"""Daily YouTube trend briefing for interest keywords."""

import os
import re
import urllib.parse
import urllib.request
import json
from datetime import datetime, timedelta, timezone

KEYWORDS = ["클로드 코드"]
MAX_RESULTS = 5


def get_api_key() -> str:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable is not set")
    return api_key


def youtube_get(path: str, params: dict) -> dict:
    url = f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def search_recent_videos(api_key: str, keyword: str) -> list[dict]:
    published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    search_data = youtube_get("search", {
        "key": api_key,
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

    stats_data = youtube_get("videos", {
        "key": api_key,
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


def main():
    api_key = get_api_key()
    results = {}

    for keyword in KEYWORDS:
        print(f"검색 중: {keyword}")
        results[keyword] = search_recent_videos(api_key, keyword)

    message = build_message(results)
    print(message)


if __name__ == "__main__":
    main()
