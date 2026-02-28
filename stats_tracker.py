#!/usr/bin/env python3
"""
Stats Tracker — the /stats command equivalent.
Pulls all platform stats, saves to history.json, generates current-state.md.
Inspired by Nadia Privalikhina's Business OS /stats command.

Usage:
    python3 stats_tracker.py                    # Full stats pull (all platforms)
    python3 stats_tracker.py --youtube-only     # Only YouTube (API, no browser)
    python3 stats_tracker.py --linkedin-only    # Only LinkedIn (needs li_at cookie)
    python3 stats_tracker.py --twitter-only     # Only Twitter (needs auth_token)
    python3 stats_tracker.py --notify           # Send summary to Telegram
    python3 stats_tracker.py --visible          # Show browsers
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

STATS_DIR = os.path.join(os.path.dirname(__file__), "stats")
HISTORY_FILE = os.path.join(STATS_DIR, "history.json")
STATE_FILE = os.path.join(STATS_DIR, "current-state.md")

os.makedirs(STATS_DIR, exist_ok=True)


def load_history():
    """Load stats history from JSON."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history(history):
    """Save stats history to JSON."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_previous_entry(history):
    """Get the most recent entry from history."""
    if not history:
        return None
    return history[-1]


def calc_delta(current, previous, key):
    """Calculate change between current and previous values."""
    curr = current.get(key)
    prev = previous.get(key) if previous else None
    if curr is not None and prev is not None:
        delta = curr - prev
        sign = "+" if delta >= 0 else ""
        return f"{curr:,} ({sign}{delta:,})"
    elif curr is not None:
        return f"{curr:,}"
    return "N/A"


def fetch_youtube_stats():
    """Fetch YouTube stats via API."""
    try:
        from youtube_stats import YouTubeStats
        yt = YouTubeStats()
        return yt.get_all_stats()
    except Exception as e:
        print(f"YouTube error: {e}", file=sys.stderr)
        return {"platform": "youtube", "error": str(e)}


def fetch_linkedin_stats(headless=True):
    """Fetch LinkedIn stats via browser."""
    try:
        from linkedin_scraper import LinkedInScraper
        scraper = LinkedInScraper(headless=headless)
        return scraper.get_all_stats()
    except Exception as e:
        print(f"LinkedIn error: {e}", file=sys.stderr)
        return {"platform": "linkedin", "error": str(e)}


def fetch_twitter_stats(headless=True):
    """Fetch Twitter stats via browser."""
    try:
        from twitter_scraper import TwitterScraper
        scraper = TwitterScraper(headless=headless)
        return scraper.get_all_stats()
    except Exception as e:
        print(f"Twitter error: {e}", file=sys.stderr)
        return {"platform": "twitter", "error": str(e)}


def generate_state_md(entry, previous):
    """Generate human-readable current-state.md."""
    now = datetime.now(timezone.utc)
    ist = now + timedelta(hours=5, minutes=30)

    lines = [
        "# Current Stats",
        f"",
        f"**Last updated:** {ist.strftime('%B %d, %Y at %I:%M %p IST')}",
        "",
        "---",
        "",
    ]

    # YouTube
    yt = entry.get("youtube", {})
    prev_yt = previous.get("youtube", {}) if previous else {}
    if not yt.get("error"):
        lines.extend([
            "## YouTube",
            f"- Subscribers: **{calc_delta(yt, prev_yt, 'subscribers')}**",
            f"- Total views: **{calc_delta(yt, prev_yt, 'total_views')}**",
            f"- Videos: **{yt.get('video_count', 'N/A')}**",
        ])
        videos = yt.get("recent_videos", [])
        if videos:
            lines.append(f"- Avg views (last {len(videos)}): **{yt.get('avg_views_recent', 'N/A')}**")
            lines.append("")
            lines.append("### Recent Videos")
            for v in videos[:5]:
                lines.append(f"- {v.get('title', '?')}: **{v.get('views', 0):,}** views, {v.get('likes', 0)} likes")
        lines.append("")
    else:
        lines.extend(["## YouTube", f"- Error: {yt.get('error')}", ""])

    # LinkedIn
    li = entry.get("linkedin", {})
    prev_li = previous.get("linkedin", {}) if previous else {}
    if not li.get("error"):
        lines.extend([
            "## LinkedIn",
            f"- Followers: **{calc_delta(li, prev_li, 'followers')}**",
            f"- Connections: **{calc_delta(li, prev_li, 'connections')}**",
        ])
        posts = li.get("recent_posts", [])
        if posts:
            lines.append(f"- Avg reactions (last {len(posts)}): **{li.get('avg_reactions', 'N/A')}**")
        lines.append("")
    elif li.get("error"):
        lines.extend(["## LinkedIn", f"- Error: {li.get('error')}", ""])

    # Twitter
    tw = entry.get("twitter", {})
    prev_tw = previous.get("twitter", {}) if previous else {}
    if not tw.get("error"):
        lines.extend([
            "## Twitter / X",
            f"- Followers: **{calc_delta(tw, prev_tw, 'followers')}**",
            f"- Following: **{tw.get('following', 'N/A')}**",
        ])
        posts = tw.get("recent_posts", [])
        if posts:
            lines.append(f"- Avg views (last {len(posts)}): **{tw.get('avg_views', 'N/A')}**")
        lines.append("")
    elif tw.get("error"):
        lines.extend(["## Twitter / X", f"- Error: {tw.get('error')}", ""])

    # Total audience
    total = 0
    for platform in [yt, li, tw]:
        for key in ["subscribers", "followers"]:
            val = platform.get(key)
            if isinstance(val, int):
                total += val

    lines.extend([
        "---",
        "",
        f"## Total Audience: **{total:,}**",
        "",
        "---",
        f"*Generated by stats_tracker.py*",
    ])

    return "\n".join(lines)


def send_telegram_notification(summary):
    """Send stats summary to Telegram."""
    import requests as req

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "637313836")

    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not set, skipping notification", file=sys.stderr)
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": summary,
        "parse_mode": "Markdown",
    }
    try:
        resp = req.post(url, json=payload, timeout=10)
        if resp.ok:
            print("Telegram notification sent", file=sys.stderr)
        else:
            print(f"Telegram error: {resp.text}", file=sys.stderr)
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Stats Tracker — /stats command")
    parser.add_argument("--youtube-only", action="store_true")
    parser.add_argument("--linkedin-only", action="store_true")
    parser.add_argument("--twitter-only", action="store_true")
    parser.add_argument("--notify", action="store_true", help="Send to Telegram")
    parser.add_argument("--visible", action="store_true", help="Show browsers")
    parser.add_argument("--no-save", action="store_true", help="Don't save to history")
    args = parser.parse_args()

    headless = not args.visible

    # Determine what to fetch
    fetch_all = not (args.youtube_only or args.linkedin_only or args.twitter_only)

    entry = {
        "date": datetime.now(timezone.utc).isoformat(),
    }

    print("=" * 50, file=sys.stderr)
    print("  Stats Tracker — AIwithDhruv", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    # Fetch each platform
    if fetch_all or args.youtube_only:
        print("\n[YouTube] Fetching...", file=sys.stderr)
        entry["youtube"] = fetch_youtube_stats()

    if fetch_all or args.linkedin_only:
        print("\n[LinkedIn] Fetching...", file=sys.stderr)
        entry["linkedin"] = fetch_linkedin_stats(headless)

    if fetch_all or args.twitter_only:
        print("\n[Twitter] Fetching...", file=sys.stderr)
        entry["twitter"] = fetch_twitter_stats(headless)

    # Load history and calculate deltas
    history = load_history()
    previous = get_previous_entry(history)

    # Save to history
    if not args.no_save:
        history.append(entry)
        save_history(history)
        print(f"\nHistory saved ({len(history)} entries total)", file=sys.stderr)

    # Generate current-state.md
    state_md = generate_state_md(entry, previous)
    with open(STATE_FILE, "w") as f:
        f.write(state_md)
    print(f"State written to {STATE_FILE}", file=sys.stderr)

    # Print summary
    print("\n" + "=" * 50)
    print(state_md)
    print("=" * 50)

    # Telegram notification
    if args.notify:
        # Build compact summary for Telegram
        lines = ["*Daily Stats — AIwithDhruv*\n"]
        yt = entry.get("youtube", {})
        li = entry.get("linkedin", {})
        tw = entry.get("twitter", {})

        if not yt.get("error"):
            lines.append(f"YouTube: {calc_delta(yt, previous.get('youtube', {}) if previous else {}, 'subscribers')} subs")
        if not li.get("error"):
            lines.append(f"LinkedIn: {calc_delta(li, previous.get('linkedin', {}) if previous else {}, 'followers')} followers")
        if not tw.get("error"):
            lines.append(f"Twitter: {calc_delta(tw, previous.get('twitter', {}) if previous else {}, 'followers')} followers")

        send_telegram_notification("\n".join(lines))

    # Output full JSON for piping
    print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()
