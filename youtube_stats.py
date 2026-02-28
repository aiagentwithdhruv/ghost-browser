#!/usr/bin/env python3
"""
YouTube stats fetcher — uses YouTube Data API v3 (FREE, 10K units/day).
No browser needed — pure API calls.

Usage:
    python3 youtube_stats.py                           # Full stats
    python3 youtube_stats.py --channel UCxxxxx         # Custom channel
    python3 youtube_stats.py --recent 10               # Last 10 videos
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

try:
    from googleapiclient.discovery import build
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

# Fallback: use requests if google-api-python-client not installed
import requests


class YouTubeStats:
    """Fetch YouTube channel stats via Data API v3."""

    API_BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key=None, channel_id=None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.channel_id = channel_id or os.getenv("YOUTUBE_CHANNEL_ID")

        if not self.api_key:
            raise ValueError(
                "YOUTUBE_API_KEY not found. Get one free at "
                "https://console.cloud.google.com/apis/credentials "
                "(enable YouTube Data API v3)"
            )

    def _api_get(self, endpoint, params):
        """Make API request using requests (no dependency on google-api-python-client)."""
        params["key"] = self.api_key
        url = f"{self.API_BASE}/{endpoint}"
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_channel_stats(self):
        """
        Get channel-level stats: subscribers, views, videos.
        Cost: 1 unit per call.
        """
        params = {
            "part": "statistics,snippet",
            "id": self.channel_id,
        }

        data = self._api_get("channels", params)
        items = data.get("items", [])
        if not items:
            # Try by username/handle
            params.pop("id")
            params["forHandle"] = self.channel_id
            data = self._api_get("channels", params)
            items = data.get("items", [])

        if not items:
            raise ValueError(f"Channel not found: {self.channel_id}")

        channel = items[0]
        stats = channel["statistics"]
        snippet = channel["snippet"]

        return {
            "channel_name": snippet.get("title"),
            "channel_id": channel["id"],
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "hidden_subs": stats.get("hiddenSubscriberCount", False),
        }

    def get_recent_videos(self, max_results=5):
        """
        Get recent video stats.
        Cost: ~3 units per call (search=100 units, so we use playlistItems instead).
        """
        # Get uploads playlist ID (costs 1 unit vs 100 for search)
        params = {
            "part": "contentDetails",
            "id": self.channel_id,
        }
        data = self._api_get("channels", params)
        items = data.get("items", [])
        if not items:
            return []

        uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Get recent uploads (1 unit)
        params = {
            "part": "snippet",
            "playlistId": uploads_playlist,
            "maxResults": max_results,
        }
        data = self._api_get("playlistItems", params)

        video_ids = [
            item["snippet"]["resourceId"]["videoId"]
            for item in data.get("items", [])
        ]

        if not video_ids:
            return []

        # Get video stats (1 unit)
        params = {
            "part": "statistics,snippet,contentDetails",
            "id": ",".join(video_ids),
        }
        data = self._api_get("videos", params)

        videos = []
        for item in data.get("items", []):
            stats = item["statistics"]
            snippet = item["snippet"]
            videos.append({
                "video_id": item["id"],
                "title": snippet.get("title"),
                "published_at": snippet.get("publishedAt"),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": item.get("contentDetails", {}).get("duration"),
            })

        return videos

    def get_all_stats(self, recent_count=5):
        """Get all YouTube stats in one call."""
        result = {
            "platform": "youtube",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            channel = self.get_channel_stats()
            result.update(channel)
        except Exception as e:
            print(f"Error getting channel stats: {e}", file=sys.stderr)
            result["error_channel"] = str(e)

        try:
            videos = self.get_recent_videos(recent_count)
            result["recent_videos"] = videos
            if videos:
                total_views = sum(v["views"] for v in videos)
                result["avg_views_recent"] = round(total_views / len(videos), 1)
        except Exception as e:
            print(f"Error getting videos: {e}", file=sys.stderr)
            result["recent_videos"] = []
            result["error_videos"] = str(e)

        return result


def main():
    parser = argparse.ArgumentParser(description="YouTube stats fetcher (API v3)")
    parser.add_argument("--channel", help="Channel ID or handle")
    parser.add_argument("--recent", type=int, default=5, help="Number of recent videos")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    fetcher = YouTubeStats(channel_id=args.channel)
    result = fetcher.get_all_stats(recent_count=args.recent)

    output = json.dumps(result, indent=2)
    print(output)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
