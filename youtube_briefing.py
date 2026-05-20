#!/usr/bin/env python3
"""Daily YouTube trend briefing for interest keywords."""

import os
import re
import subprocess
from datetime import datetime, timedelta, timezone

import requests

KEYWORDS = ["클로드 코드"]
RECIPIENT = "010-9703-8710"
MAX_RESULTS = 5
YT_BASE = "https://www.googleapis.com/youtube/v3"


def get_api_key() -> str:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable is not set")
    return key


def search_recent_videos(api_key: str, keyword: str) -> list[dict]:
    published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    r = requests.get(
        f"{YT_BASE}/search",
        params={
            "key": api_key,
            "q": keyword,
            "part": "snippet",
            "type": "video",
            "publishedAfter": published_after,
            "maxResults": MAX_RESULTS,
            "order": "relevance",
        },
        timeout=10,
    )
    r.raise_for_status()

    video_ids = [item["id"]["videoId"] for item in r.json().get("items", [])]
    if not video_ids:
        return []

    r2 = requests.get(
        f"{YT_BASE}/videos",
        params={"key": api_key, "id": ",".join(video_ids), "part": "statistics,snippet"},
        timeout=10,
    )
    r2.raise_for_status()

    videos = []
    for item in r2.json().get("items", []):
        videos.append(
            {
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "url": "https://youtu.be/" + item["id"],
            }
        )

    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos[:MAX_RESULTS]


def analyze_title_patterns(titles: list[str]) -> list[str]:
    patterns = []

    n = sum(1 for t in titles if re.search(r"\d+", t))
    if n:
        patterns.append(f"숫자 포함형 {n}개")

    q = sum(1 for t in titles if re.search(r"[?？]|방법|어떻게|뭔가|무엇|왜|어디", t))
    if q:
        patterns.append(f"질문형 {q}개")

    c = sum(1 for t in titles if re.search(r"vs|비교|차이|대비|versus", t, re.IGNORECASE))
    if c:
        patterns.append(f"비교형 {c}개")

    tu = sum(
        1 for t in titles if re.search(r"튜토리얼|tutorial|강의|가이드|사용법|입문|시작", t, re.IGNORECASE)
    )
    if tu:
        patterns.append(f"튜토리얼/가이드형 {tu}개")

    rv = sum(
        1 for t in titles if re.search(r"리뷰|review|후기|사용기|써보니|써봤", t, re.IGNORECASE)
    )
    if rv:
        patterns.append(f"리뷰/후기형 {rv}개")

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
            lines.append(f"  {i}. {v['title']}")
            lines.append(f"     채널: {v['channel']} | 조회수: {v['views']:,}")
            lines.append(f"     {v['url']}")

        titles = [v["title"] for v in videos]
        patterns = analyze_title_patterns(titles)
        lines.append(f"\n  [제목 패턴] {', '.join(patterns)}\n")

    return "\n".join(lines)


def send_imessage(phone: str, message: str) -> None:
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{phone}" of targetService
        send "{message}" to targetBuddy
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"iMessage 전송 실패: {result.stderr.strip()}")


def main():
    api_key = get_api_key()
    results = {}

    for keyword in KEYWORDS:
        print(f"검색 중: {keyword}")
        results[keyword] = search_recent_videos(api_key, keyword)

    message = build_message(results)
    print(message)

    send_imessage(RECIPIENT, message)
    print("iMessage 전송 완료")


if __name__ == "__main__":
    main()
