#!/usr/bin/env python3
"""
Multi-Context Browser Manager — Run multiple isolated browser sessions.

Inspired by Manus AI's sandboxed containers + Playwright's native browser contexts.
Each agent gets its own isolated context (cookies, storage, viewport) within a single
browser process — efficient and undetectable.

Playwright's sync API is single-threaded (greenlet-based), so tasks run sequentially
but each in its own isolated browser context. The audience sees multiple browser
windows open simultaneously — each doing its own thing.

Usage:
    manager = MultiContextManager()
    manager.start()
    s1 = manager.create_session("linkedin", cookies=[...])
    s2 = manager.create_session("scraper")
    results = manager.run_parallel([
        ("linkedin", linkedin_task),
        ("scraper", scraper_task),
    ])
    manager.stop()
"""

import os
import sys
import time
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

from human_behavior import HumanBehavior


class BrowserSession:
    """A single isolated browser context with its own cookies, storage, and page."""

    def __init__(self, name, context, page, viewport):
        self.name = name
        self.context = context
        self.page = page
        self.viewport = viewport
        self.created_at = datetime.now()
        self.action_count = 0
        self.status = "idle"
        self.last_url = None
        self.log = []

    def _log(self, msg):
        self.log.append({"time": datetime.now().isoformat(), "msg": msg})
        print(f"  [{self.name}] {msg}", file=sys.stderr)

    def goto(self, url, settle=2):
        self.status = "running"
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self.last_url = url
        HumanBehavior.random_delay(settle * 0.7, settle * 1.3)
        self._log(f"→ {url[:60]}")

    def evaluate(self, js, arg=None):
        if arg is not None:
            return self.page.evaluate(js, arg)
        return self.page.evaluate(js)

    def screenshot(self, path=None):
        if not path:
            os.makedirs("/tmp/ghost-browser", exist_ok=True)
            path = f"/tmp/ghost-browser/{self.name}_{datetime.now().strftime('%H%M%S')}.png"
        self.page.screenshot(path=path, full_page=False)
        self._log(f"screenshot → {path}")
        return path

    def scroll(self, direction="down", distance=600):
        HumanBehavior.human_scroll(self.page, direction, distance)

    def type_text(self, selector, text, wpm=45):
        HumanBehavior.human_type(self.page, selector, text, wpm=wpm)

    def click(self, selector):
        HumanBehavior.human_click(self.page, selector)

    def tick(self):
        self.action_count += 1


class MultiContextManager:
    """
    Manages multiple isolated browser sessions within a single browser instance.
    Each session is a separate Playwright BrowserContext — isolated cookies,
    localStorage, viewport. Runs 5-20 agents without opening 20 Chrome processes.
    """

    def __init__(self, headless=False, max_sessions=10):
        self.headless = headless
        self.max_sessions = max_sessions
        self.sessions = {}
        self._playwright = None
        self._browser = None

    def start(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        print(f"Ghost Browser started (headless={self.headless})", file=sys.stderr)

    def stop(self):
        for name in list(self.sessions.keys()):
            self.close_session(name)
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        print("Ghost Browser stopped", file=sys.stderr)

    def create_session(self, name, cookies=None, viewport=None, user_agent=None):
        if name in self.sessions:
            raise ValueError(f"Session '{name}' already exists")
        if len(self.sessions) >= self.max_sessions:
            raise RuntimeError(f"Max sessions ({self.max_sessions}) reached")

        viewport = viewport or HumanBehavior.random_viewport()
        context_opts = {"viewport": viewport}
        if user_agent:
            context_opts["user_agent"] = user_agent

        context = self._browser.new_context(**context_opts)
        if cookies:
            context.add_cookies(cookies)

        page = context.new_page()
        session = BrowserSession(name, context, page, viewport)
        self.sessions[name] = session
        print(f"  [{name}] Session created ({viewport['width']}x{viewport['height']})", file=sys.stderr)
        return session

    def close_session(self, name):
        session = self.sessions.pop(name, None)
        if session:
            try:
                session.context.close()
            except Exception:
                pass
            print(f"  [{name}] Session closed", file=sys.stderr)

    def get_session(self, name):
        return self.sessions.get(name)

    def list_sessions(self):
        return [{
            "name": n, "status": s.status, "actions": s.action_count,
            "url": s.last_url, "viewport": s.viewport,
        } for n, s in self.sessions.items()]

    def run_parallel(self, tasks):
        """
        Run tasks across isolated sessions. Each task runs in its own browser
        context sequentially (Playwright sync constraint), but all windows
        stay open — the audience sees multiple pages simultaneously.
        """
        results = {}
        for name, fn in tasks:
            session = self.get_session(name)
            if not session:
                results[name] = {"error": f"Session '{name}' not found"}
                continue
            try:
                session.status = "running"
                result = fn(session)
                session.status = "done"
                results[name] = {"result": result}
                print(f"  [{name}] done", file=sys.stderr)
            except Exception as e:
                session.status = "error"
                results[name] = {"error": str(e)}
                print(f"  [{name}] error: {e}", file=sys.stderr)
        return results

    def screenshot_all(self):
        shots = {}
        for name, session in self.sessions.items():
            try:
                shots[name] = session.screenshot()
            except Exception as e:
                shots[name] = f"error: {e}"
        return shots

    # ── Pre-built Session Factories ────────────────────────

    def create_linkedin_session(self, li_at=None):
        li_at = li_at or os.getenv("LINKEDIN_LI_AT")
        if not li_at:
            raise ValueError("LINKEDIN_LI_AT not set")
        return self.create_session("linkedin", cookies=[{
            "name": "li_at", "value": li_at,
            "domain": ".linkedin.com", "path": "/",
        }], viewport={"width": 1440, "height": 900})

    def create_scraper_session(self, name="scraper"):
        return self.create_session(name, viewport={"width": 1920, "height": 1080})

    def create_demo_session(self, name="demo"):
        return self.create_session(name, viewport={"width": 1440, "height": 900})


if __name__ == "__main__":
    print("Ghost Browser — Multi-Context Test")
    print("=" * 50)

    manager = MultiContextManager(headless=False)
    manager.start()
    try:
        manager.create_session("google", viewport={"width": 1440, "height": 900})
        manager.create_session("github", viewport={"width": 1920, "height": 1080})
        manager.create_session("hackernews", viewport={"width": 1366, "height": 768})

        results = manager.run_parallel([
            ("google", lambda s: (
                s.goto("https://www.google.com"),
                s.type_text('textarea[name="q"]', "Ghost Browser AI automation", wpm=40),
                s.page.keyboard.press("Enter"),
                HumanBehavior.random_delay(2, 3),
                "Google search done"
            )[-1]),
            ("github", lambda s: (
                s.goto("https://github.com/trending"),
                s.scroll("down", 600),
                "GitHub trending browsed"
            )[-1]),
            ("hackernews", lambda s: (
                s.goto("https://news.ycombinator.com"),
                s.scroll("down", 300),
                "Hacker News read"
            )[-1]),
        ])

        print(f"\nResults: {results}")
        shots = manager.screenshot_all()
        print(f"Screenshots: {shots}")
        print("\nBrowser stays open 15s...")
        time.sleep(15)
    finally:
        manager.stop()
