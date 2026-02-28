#!/usr/bin/env python3
"""
Base browser class for Playwright-based scraping.
Adapted from skool-monitor pattern — cookie-based auth, headless Chrome, context manager.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright


class BaseBrowser:
    """
    Reusable Playwright browser with cookie-based authentication.
    Usage:
        with BaseBrowser(cookies=[...]) as browser:
            browser.goto("https://example.com")
            content = browser.page.content()
    """

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )

    def __init__(self, cookies=None, headless=True, viewport=None):
        self.cookies = cookies or []
        self.headless = headless
        self.viewport = viewport or {"width": 1440, "height": 900}
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        """Launch browser and create authenticated context."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent=self.USER_AGENT,
            viewport=self.viewport,
            locale="en-US",
        )
        if self.cookies:
            self.context.add_cookies(self.cookies)
        self.page = self.context.new_page()
        return self

    def goto(self, url, wait_until="domcontentloaded", timeout=30000, settle=2):
        """Navigate to URL and wait for page to settle."""
        self.page.goto(url, wait_until=wait_until, timeout=timeout)
        if settle:
            time.sleep(settle)

    def screenshot(self, path, full_page=False, element=None):
        """Take screenshot of page or specific element."""
        if element:
            locator = self.page.locator(element)
            locator.screenshot(path=path)
        else:
            self.page.screenshot(path=path, full_page=full_page)
        return path

    def evaluate(self, js_code, arg=None):
        """Run JavaScript in page context, optionally passing an argument."""
        if arg is not None:
            return self.page.evaluate(js_code, arg)
        return self.page.evaluate(js_code)

    def get_text(self, selector, timeout=5000):
        """Get text content of an element."""
        try:
            el = self.page.wait_for_selector(selector, timeout=timeout)
            return el.text_content().strip() if el else None
        except Exception:
            return None

    def get_all_text(self, selector, timeout=5000):
        """Get text content of all matching elements."""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            elements = self.page.query_selector_all(selector)
            return [el.text_content().strip() for el in elements if el.text_content()]
        except Exception:
            return []

    def click(self, selector, timeout=5000):
        """Click an element after waiting for it."""
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()

    def fill(self, selector, text, timeout=5000):
        """Fill an input element after waiting for it."""
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.fill(text)

    def wait_and_click(self, selector, timeout=10000):
        """Wait longer for an element, then click. For dynamic content."""
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()

    def stop(self):
        """Clean up all resources."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
