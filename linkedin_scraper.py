#!/usr/bin/env python3
"""
LinkedIn stats scraper — extracts follower count, profile views, and recent post impressions.
Uses li_at cookie for authentication (get from browser DevTools → Application → Cookies).

Usage:
    python3 linkedin_scraper.py                    # Full scrape (followers + posts)
    python3 linkedin_scraper.py --followers-only   # Just follower count
    python3 linkedin_scraper.py --visible           # Show browser window
    python3 linkedin_scraper.py --output stats.json # Save to custom file
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

# Add parent dir for base_browser import
sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass


class LinkedInScraper:
    """Scrape LinkedIn profile stats using Playwright + li_at cookie."""

    def __init__(self, li_at=None, profile_url=None, headless=True):
        self.li_at = li_at or os.getenv("LINKEDIN_LI_AT")
        self.profile_url = profile_url or os.getenv(
            "LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/aiwithdhruv/"
        )
        if not self.li_at:
            raise ValueError(
                "LINKEDIN_LI_AT not found. Get it from browser DevTools → "
                "Application → Cookies → linkedin.com → li_at"
            )
        self.headless = headless
        self.browser = None

    def _make_cookies(self):
        return [
            {
                "name": "li_at",
                "value": self.li_at,
                "domain": ".linkedin.com",
                "path": "/",
            }
        ]

    def get_follower_count(self):
        """
        Scrape follower count from LinkedIn profile page.
        Returns dict with follower_count and connection_count.
        """
        print("Fetching LinkedIn follower count...", file=sys.stderr)

        with BaseBrowser(cookies=self._make_cookies(), headless=self.headless) as b:
            b.goto(self.profile_url, settle=3)

            # Check if we're on a login page (cookie expired)
            current_url = b.page.url
            if "/login" in current_url or "/checkpoint" in current_url:
                raise ValueError(
                    "LinkedIn redirected to login — li_at cookie expired. "
                    "Get a fresh one from browser DevTools."
                )

            # Try multiple selectors for follower count
            # LinkedIn changes DOM frequently, so we try several approaches
            stats = {"followers": None, "connections": None}

            # Method 1: Look for follower text in profile header
            follower_text = b.get_text("span.t-bold:has(+ span:text-matches('follower'))")
            if not follower_text:
                # Method 2: Evaluate JS to find follower count in page
                follower_text = b.evaluate("""
                    () => {
                        // Search for "X followers" pattern in visible text
                        const walker = document.createTreeWalker(
                            document.body, NodeFilter.SHOW_TEXT
                        );
                        while (walker.nextNode()) {
                            const text = walker.currentNode.textContent.trim();
                            const match = text.match(/([\\d,]+)\\s+follower/i);
                            if (match) return match[1];
                        }
                        return null;
                    }
                """)

            if follower_text:
                stats["followers"] = int(follower_text.replace(",", "").replace(".", ""))

            # Look for connections count
            conn_text = b.evaluate("""
                () => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT
                    );
                    while (walker.nextNode()) {
                        const text = walker.currentNode.textContent.trim();
                        const match = text.match(/([\\d,]+)\\+?\\s+connection/i);
                        if (match) return match[1];
                    }
                    return null;
                }
            """)
            if conn_text:
                stats["connections"] = int(conn_text.replace(",", "").replace("+", "").replace(".", ""))

            # Fallback: screenshot the profile for manual reading
            if stats["followers"] is None:
                screenshot_path = os.path.join(
                    os.path.dirname(__file__), "stats", "linkedin_profile.png"
                )
                b.screenshot(screenshot_path)
                print(
                    f"Could not auto-extract followers. Screenshot saved: {screenshot_path}",
                    file=sys.stderr,
                )

            return stats

    def get_post_analytics(self, max_posts=5):
        """
        Scrape recent post performance from LinkedIn analytics page.
        Returns list of post dicts with impressions, reactions, comments.
        """
        print(f"Fetching analytics for last {max_posts} posts...", file=sys.stderr)

        with BaseBrowser(cookies=self._make_cookies(), headless=self.headless) as b:
            # Navigate to the analytics/posts page
            analytics_url = self.profile_url.rstrip("/") + "/recent-activity/all/"
            b.goto(analytics_url, settle=4)

            # Scroll to load posts
            for _ in range(3):
                b.page.keyboard.press("End")
                time.sleep(1.5)

            # Extract post data from the feed
            posts = b.evaluate("""
                (maxPosts) => {
                    const results = [];
                    // LinkedIn feed items
                    const items = document.querySelectorAll(
                        '[data-urn*="activity"], .feed-shared-update-v2, .occludable-update'
                    );

                    for (let i = 0; i < Math.min(items.length, maxPosts); i++) {
                        const item = items[i];
                        const text = item.innerText || '';

                        // Extract engagement numbers
                        const likesMatch = text.match(/(\\d+)\\s*(?:like|reaction)/i);
                        const commentsMatch = text.match(/(\\d+)\\s*comment/i);
                        const repostsMatch = text.match(/(\\d+)\\s*repost/i);

                        // Get post preview text
                        const contentEl = item.querySelector(
                            '.feed-shared-text, .break-words, .update-components-text'
                        );
                        const preview = contentEl
                            ? contentEl.textContent.trim().substring(0, 100)
                            : text.substring(0, 100);

                        results.push({
                            preview: preview,
                            reactions: likesMatch ? parseInt(likesMatch[1]) : 0,
                            comments: commentsMatch ? parseInt(commentsMatch[1]) : 0,
                            reposts: repostsMatch ? parseInt(repostsMatch[1]) : 0,
                        });
                    }
                    return results;
                }
            """, max_posts)

            return posts

    def get_all_stats(self):
        """Get all LinkedIn stats in one call."""
        result = {
            "platform": "linkedin",
            "profile_url": self.profile_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            follower_data = self.get_follower_count()
            result.update(follower_data)
        except Exception as e:
            print(f"Error getting followers: {e}", file=sys.stderr)
            result["followers"] = None
            result["error_followers"] = str(e)

        try:
            posts = self.get_post_analytics()
            result["recent_posts"] = posts
            if posts:
                total_reactions = sum(p.get("reactions", 0) for p in posts)
                result["avg_reactions"] = round(total_reactions / len(posts), 1)
        except Exception as e:
            print(f"Error getting post analytics: {e}", file=sys.stderr)
            result["recent_posts"] = []
            result["error_posts"] = str(e)

        return result


def main():
    parser = argparse.ArgumentParser(description="LinkedIn stats scraper")
    parser.add_argument("--followers-only", action="store_true", help="Only get follower count")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    args = parser.parse_args()

    scraper = LinkedInScraper(headless=not args.visible)

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
