#!/usr/bin/env python3
"""
Twitter/X stats scraper — extracts follower count and recent post impressions.
Uses auth_token + ct0 cookies for authentication.

Usage:
    python3 twitter_scraper.py                     # Full scrape
    python3 twitter_scraper.py --followers-only    # Just follower count
    python3 twitter_scraper.py --visible           # Show browser
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass


class TwitterScraper:
    """Scrape Twitter/X profile stats using Playwright + auth cookies."""

    def __init__(self, auth_token=None, ct0=None, username=None, headless=True):
        self.auth_token = auth_token or os.getenv("TWITTER_AUTH_TOKEN")
        self.ct0 = ct0 or os.getenv("TWITTER_CT0")
        self.username = username or os.getenv("TWITTER_USERNAME", "aiwithdhruv")
        if not self.auth_token:
            raise ValueError(
                "TWITTER_AUTH_TOKEN not found. Get from browser DevTools → "
                "Application → Cookies → x.com → auth_token"
            )
        self.headless = headless

    def _make_cookies(self):
        cookies = [
            {
                "name": "auth_token",
                "value": self.auth_token,
                "domain": ".x.com",
                "path": "/",
            }
        ]
        if self.ct0:
            cookies.append({
                "name": "ct0",
                "value": self.ct0,
                "domain": ".x.com",
                "path": "/",
            })
        return cookies

    def get_follower_count(self):
        """Scrape follower/following count from Twitter profile."""
        print(f"Fetching Twitter stats for @{self.username}...", file=sys.stderr)

        with BaseBrowser(cookies=self._make_cookies(), headless=self.headless) as b:
            b.goto(f"https://x.com/{self.username}", settle=4)

            stats = {"followers": None, "following": None, "tweets": None}

            # Extract from page using JS — look for the stats in profile header
            data = b.evaluate("""
                () => {
                    const result = {};
                    const links = document.querySelectorAll('a[href*="/followers"], a[href*="/following"], a[href*="/verified_followers"]');

                    for (const link of links) {
                        const text = link.textContent.trim();
                        const href = link.getAttribute('href') || '';

                        // Parse "X Following" or "X Followers"
                        const numMatch = text.match(/([\\d,.KkMm]+)/);
                        const num = numMatch ? numMatch[1] : null;

                        if (href.includes('/following') && !href.includes('follower')) {
                            result.following = num;
                        } else if (href.includes('/follower')) {
                            result.followers = num;
                        }
                    }

                    // Tweet count from profile header
                    const tweetCount = document.querySelector('[data-testid="UserProfileHeader_Items"] + div, h2 + div');
                    if (tweetCount) {
                        const match = tweetCount.textContent.match(/([\\d,.KkMm]+)\\s*(?:post|tweet)/i);
                        if (match) result.tweets = match[1];
                    }

                    return result;
                }
            """)

            # Parse K/M suffixes
            for key in ["followers", "following", "tweets"]:
                val = data.get(key)
                if val:
                    stats[key] = self._parse_count(val)

            # Fallback screenshot
            if stats["followers"] is None:
                screenshot_path = os.path.join(
                    os.path.dirname(__file__), "stats", "twitter_profile.png"
                )
                b.screenshot(screenshot_path)
                print(
                    f"Could not auto-extract. Screenshot saved: {screenshot_path}",
                    file=sys.stderr,
                )

            return stats

    def get_recent_posts(self, max_posts=5):
        """Scrape recent post impressions from profile."""
        print(f"Fetching recent posts for @{self.username}...", file=sys.stderr)

        with BaseBrowser(cookies=self._make_cookies(), headless=self.headless) as b:
            b.goto(f"https://x.com/{self.username}", settle=4)

            # Scroll to load posts
            for _ in range(2):
                b.page.keyboard.press("End")
                time.sleep(2)

            posts = b.evaluate("""
                (maxPosts) => {
                    const results = [];
                    const articles = document.querySelectorAll('article[data-testid="tweet"]');

                    for (let i = 0; i < Math.min(articles.length, maxPosts); i++) {
                        const article = articles[i];
                        const text = article.querySelector('[data-testid="tweetText"]');
                        const preview = text ? text.textContent.substring(0, 100) : '';

                        // Get engagement stats from aria labels
                        const stats = {};
                        const groups = article.querySelectorAll('[role="group"] button');
                        const labels = ['replies', 'reposts', 'likes', 'views', 'bookmarks'];

                        groups.forEach((btn, idx) => {
                            const aria = btn.getAttribute('aria-label') || '';
                            const match = aria.match(/(\\d+)/);
                            if (match && labels[idx]) {
                                stats[labels[idx]] = parseInt(match[1]);
                            }
                        });

                        results.push({ preview, ...stats });
                    }
                    return results;
                }
            """, max_posts)

            return posts

    def get_all_stats(self):
        """Get all Twitter stats."""
        result = {
            "platform": "twitter",
            "username": self.username,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            follower_data = self.get_follower_count()
            result.update(follower_data)
        except Exception as e:
            print(f"Error getting followers: {e}", file=sys.stderr)
            result["error_followers"] = str(e)

        try:
            posts = self.get_recent_posts()
            result["recent_posts"] = posts
            if posts:
                total_views = sum(p.get("views", 0) for p in posts)
                result["avg_views"] = round(total_views / len(posts), 1) if posts else 0
        except Exception as e:
            print(f"Error getting posts: {e}", file=sys.stderr)
            result["recent_posts"] = []

        return result

    @staticmethod
    def _parse_count(text):
        """Parse '1.2K' / '3.5M' / '1,234' into int."""
        text = text.strip().replace(",", "")
        multiplier = 1
        if text.upper().endswith("K"):
            multiplier = 1000
            text = text[:-1]
        elif text.upper().endswith("M"):
            multiplier = 1000000
            text = text[:-1]
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return None


def main():
    parser = argparse.ArgumentParser(description="Twitter/X stats scraper")
    parser.add_argument("--followers-only", action="store_true")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()

    scraper = TwitterScraper(headless=not args.visible)

    if args.followers_only:
        result = scraper.get_follower_count()
    else:
        result = scraper.get_all_stats()

    output = json.dumps(result, indent=2)
    print(output)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
