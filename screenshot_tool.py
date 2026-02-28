#!/usr/bin/env python3
"""
Screenshot utility — capture full-page or element screenshots of any URL.
Used for Favikon rankings, media kit assets, competitor analysis.

Usage:
    python3 screenshot_tool.py https://favikon.com/creator/aiwithdhruv
    python3 screenshot_tool.py https://example.com --element ".stats-card" --output card.png
    python3 screenshot_tool.py https://example.com --full-page --output full.png
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass


class ScreenshotTool:
    """Take screenshots of any URL with optional element targeting."""

    def __init__(self, headless=True, viewport=None):
        self.headless = headless
        self.viewport = viewport or {"width": 1440, "height": 900}

    def capture(self, url, output=None, full_page=False, element=None,
                cookies=None, wait=3, viewport=None):
        """
        Capture screenshot of a URL.

        Args:
            url: URL to screenshot
            output: Output file path (auto-generated if None)
            full_page: Capture full scrollable page
            element: CSS selector to screenshot specific element
            cookies: Optional list of cookie dicts for auth
            wait: Seconds to wait after page load
            viewport: Override viewport size {"width": int, "height": int}

        Returns:
            Path to saved screenshot
        """
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = url.split("//")[-1].split("/")[0].replace(".", "_")
            output = os.path.join(
                os.path.dirname(__file__), "stats",
                f"screenshot_{domain}_{timestamp}.png"
            )

        os.makedirs(os.path.dirname(output), exist_ok=True)

        vp = viewport or self.viewport
        with BaseBrowser(cookies=cookies or [], headless=self.headless, viewport=vp) as b:
            b.goto(url, settle=wait)

            if element:
                b.screenshot(output, element=element)
            else:
                b.screenshot(output, full_page=full_page)

        print(f"Screenshot saved: {output}", file=sys.stderr)
        return output

    def capture_favikon(self, profile_url=None, output=None):
        """Capture Favikon creator profile screenshot."""
        url = profile_url or os.getenv(
            "FAVIKON_PROFILE_URL", "https://favikon.com/creator/aiwithdhruv"
        )
        if output is None:
            output = os.path.join(
                os.path.dirname(__file__), "stats",
                f"favikon_{datetime.now().strftime('%Y%m%d')}.png"
            )
        return self.capture(url, output=output, full_page=True, wait=5)

    def capture_linkedin_profile(self, li_at=None, profile_url=None, output=None):
        """Capture LinkedIn profile screenshot (needs auth)."""
        li_at = li_at or os.getenv("LINKEDIN_LI_AT")
        url = profile_url or os.getenv(
            "LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/aiwithdhruv/"
        )
        cookies = [{"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"}] if li_at else []

        if output is None:
            output = os.path.join(
                os.path.dirname(__file__), "stats",
                f"linkedin_{datetime.now().strftime('%Y%m%d')}.png"
            )
        return self.capture(url, output=output, cookies=cookies, wait=4)

    def capture_twitter_profile(self, auth_token=None, username=None, output=None):
        """Capture Twitter/X profile screenshot (needs auth)."""
        auth_token = auth_token or os.getenv("TWITTER_AUTH_TOKEN")
        username = username or os.getenv("TWITTER_USERNAME", "aiwithdhruv")
        url = f"https://x.com/{username}"
        cookies = [{"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"}] if auth_token else []

        if output is None:
            output = os.path.join(
                os.path.dirname(__file__), "stats",
                f"twitter_{datetime.now().strftime('%Y%m%d')}.png"
            )
        return self.capture(url, output=output, cookies=cookies, wait=4)


def main():
    parser = argparse.ArgumentParser(description="Screenshot utility")
    parser.add_argument("url", nargs="?", help="URL to screenshot")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--full-page", action="store_true", help="Full page screenshot")
    parser.add_argument("--element", "-e", help="CSS selector for element screenshot")
    parser.add_argument("--wait", type=int, default=3, help="Wait time after load (seconds)")
    parser.add_argument("--visible", action="store_true", help="Show browser")
    parser.add_argument("--width", type=int, default=1440, help="Viewport width")
    parser.add_argument("--height", type=int, default=900, help="Viewport height")

    # Preset modes
    parser.add_argument("--favikon", action="store_true", help="Screenshot Favikon profile")
    parser.add_argument("--linkedin", action="store_true", help="Screenshot LinkedIn profile")
    parser.add_argument("--twitter", action="store_true", help="Screenshot Twitter profile")

    args = parser.parse_args()

    tool = ScreenshotTool(
        headless=not args.visible,
        viewport={"width": args.width, "height": args.height}
    )

    if args.favikon:
        path = tool.capture_favikon(output=args.output)
    elif args.linkedin:
        path = tool.capture_linkedin_profile(output=args.output)
    elif args.twitter:
        path = tool.capture_twitter_profile(output=args.output)
    elif args.url:
        path = tool.capture(
            args.url, output=args.output, full_page=args.full_page,
            element=args.element, wait=args.wait
        )
    else:
        parser.print_help()
        sys.exit(1)

    print(path)


if __name__ == "__main__":
    main()
