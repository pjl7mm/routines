#!/usr/bin/env python3
"""Daily YouTube trend briefing for interest keywords."""

import os
import re
import requests
from datetime import datetime, timedelta, timezone

KEYWORDS = ["클로드 코드"]
MAX_RESULTS = 5
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def get_api_key() -> str:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable is not set")
    return api_key


def search_recent_videos(api_key: str, keyword: str) -> list[dict]:
    published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    search_resp = requests.get(
        YOUTUBE_SEARCH_URL,
        params={
            "key": api_key,
            "q": keyword,
            "part": "snippet",
            "type": "video",
            "publishedAfter": published_after,
            "maxResults": MAX_RESULTS,
            "order": "relevance",
        },
        timeout=15,
    )
    search_resp.raise_for_status()
    items = search_resp.json().get("items", [])

    video_ids = [item["id"]["videoId"] for item in items]
    if not video_ids:
        return []

    stats_resp = requests.get(
        YOUTUBE_VIDEOS_URL,
        params={
            "key": api_key,
            "id": ",".join(video_ids),
            "part": "statistics,snippet",
        },
        timeout=15,
    )
    stats_resp.raise_for_status()

    videos = []
    for item in stats_resp.json().get("items", []):
        videos.append(
            {
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "video_id": item["id"],
            }
        )

    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos[:MAX_RESULTS]


def analyze_title_patterns(titles: list[str]) -> list[str]:
    patterns = []

    number_count = sum(1 for t in titles if re.search(r"\d+", t))
    if number_count:
        patterns.append(f"숫자 포함형 {number_count}개")

    question_count = sum(
        1 for t in titles if re.search(r"[?？]|방법|어떻게|뭔가|무엇|왜|어디", t)
    )
    if question_count:
        patterns.append(f"질문형 {question_count}개")

    compare_count = sum(
        1 for t in titles if re.search(r"vs|비교|차이|대비|versus", t, re.IGNORECASE)
    )
    if compare_count:
        patterns.append(f"비교형 {compare_count}개")

    tutorial_count = sum(
        1
        for t in titles
        if re.search(r"튜토리얼|tutorial|강의|가이드|사용법|입문|시작", t, re.IGNORECASE)
    )
    if tutorial_count:
        patterns.append(f"튜토리얼/가이드형 {tutorial_count}개")

    review_count = sum(
        1
        for t in titles
        if re.search(r"리뷰|review|후기|사용기|써보니|써봤", t, re.IGNORECASE)
    )
    if review_count:
        patterns.append(f"리뷰/후기형 {review_count}개")

    if not patterns:
        patterns.append("특이 패턴 없음")

    return patterns


def build_report(results: dict[str, list[dict]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"[유튜브 트렌드 브리핑] {now}\n"]

    for keyword, videos in results.items():
        lines.append(f"■ 키워드: {keyword}")
        if not videos:
            lines.append("  최근 24시간 내 업로드된 영상 없음\n")
            continue

        for i, v in enumerate(videos, 1):
            views = f"{v['views']:,}"
            lines.append(f"  {i}. {v['title']}")
            lines.append(f"     채널: {v['channel']} | 조회수: {views}")

        titles = [v["title"] for v in videos]
        patterns = analyze_title_patterns(titles)
        lines.append(f"  [제목 패턴] {', '.join(patterns)}\n")

    return "\n".join(lines)


def save_report(report: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(script_dir, f"briefing_{date_str}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(report)
    return log_path


def main():
    api_key = get_api_key()
    results = {}

    for keyword in KEYWORDS:
        print(f"검색 중: {keyword} (최근 24시간)")
        results[keyword] = search_recent_videos(api_key, keyword)

    report = build_report(results)
    print(report)

    log_path = save_report(report)
    print(f"브리핑 저장 완료: {log_path}")


if __name__ == "__main__":
    main()
