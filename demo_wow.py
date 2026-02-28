#!/usr/bin/env python3
"""
Browser Automation Demo — The "WOW" Factor
Watch the browser come alive like a ghost is controlling it.
Perfect for showing family how automation works.
"""

import sys
import os
import time
import random
import math

sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser
from human_behavior import HumanBehavior

DEMO_DIR = os.path.join(os.path.dirname(__file__), "demo_screenshots")
os.makedirs(DEMO_DIR, exist_ok=True)


def typewriter(page, selector, text, speed=0.08):
    """Visible ghost-typing effect — fast enough to be cool, slow enough to see."""
    el = page.locator(selector).first
    el.click()
    time.sleep(0.3)
    for char in text:
        page.keyboard.type(char, delay=0)
        delay = speed * random.uniform(0.6, 1.5)
        if char in " .,!?":
            delay *= 2
        time.sleep(delay)


def smooth_scroll(page, distance=800, steps=40):
    """Buttery smooth scroll animation."""
    for i in range(steps):
        progress = i / steps
        # Ease in-out curve
        ease = 0.5 - 0.5 * math.cos(progress * math.pi)
        chunk = int(distance / steps * (0.3 + 1.4 * ease))
        page.evaluate(f"window.scrollBy(0, {chunk})")
        time.sleep(0.03)


def demo_google_search(page):
    """Ghost searches Google — types query letter by letter."""
    print("\n  [1/6] Google Search — watch the ghost type...")
    page.goto("https://www.google.com", wait_until="domcontentloaded")
    time.sleep(2)

    # Type search query character by character
    search_box = page.locator('textarea[name="q"], input[name="q"]').first
    search_box.click()
    time.sleep(0.5)

    query = "How to build AI agents with Python 2026"
    for char in query:
        page.keyboard.type(char, delay=0)
        time.sleep(random.uniform(0.06, 0.15))

    time.sleep(1)
    page.keyboard.press("Enter")
    time.sleep(3)

    # Scroll through results smoothly
    smooth_scroll(page, 600)
    time.sleep(1)
    smooth_scroll(page, 400)
    print("    Done! Searched and scrolled through results")


def demo_wikipedia_speed_read(page):
    """Open Wikipedia and speed-read an article — highlight text as we go."""
    print("\n  [2/6] Wikipedia Speed Reader — highlighting text live...")
    page.goto("https://en.wikipedia.org/wiki/Artificial_intelligence", wait_until="domcontentloaded")
    time.sleep(2)

    # Smooth scroll while reading
    for i in range(5):
        smooth_scroll(page, 400, steps=30)
        time.sleep(0.8)

    # Highlight a key paragraph with JS
    page.evaluate("""
        () => {
            const paragraphs = document.querySelectorAll('#mw-content-text p');
            for (let i = 1; i < Math.min(4, paragraphs.length); i++) {
                const p = paragraphs[i];
                if (p.textContent.length > 100) {
                    p.style.transition = 'all 0.5s ease';
                    p.style.backgroundColor = '#fff3cd';
                    p.style.padding = '8px';
                    p.style.borderRadius = '4px';
                    p.style.borderLeft = '4px solid #ffc107';
                    break;
                }
            }
        }
    """)
    time.sleep(2)
    print("    Done! Read and highlighted key info")


def demo_github_explore(page):
    """Browse GitHub trending repos — the ghost explores code."""
    print("\n  [3/6] GitHub Trending — browsing popular repos...")
    page.goto("https://github.com/trending", wait_until="domcontentloaded")
    time.sleep(3)

    # Smooth scroll through trending repos
    smooth_scroll(page, 500, steps=35)
    time.sleep(1.5)
    smooth_scroll(page, 500, steps=35)
    time.sleep(1)

    # Click on the first trending repo
    try:
        first_repo = page.locator('article h2 a').first
        if first_repo.is_visible(timeout=3000):
            first_repo.click()
            time.sleep(3)
            smooth_scroll(page, 600, steps=30)
            time.sleep(1)
            print("    Done! Browsed trending repos and opened top one")
    except Exception:
        print("    Browsed trending repos")


def demo_typing_test(page):
    """Take a typing test — bot types at superhuman speed."""
    print("\n  [4/6] Speed Typing — watch the bot type at 150 WPM...")
    page.goto("https://monkeytype.com", wait_until="domcontentloaded")
    time.sleep(3)

    # Accept cookie consent if present
    try:
        consent = page.locator('button:has-text("Accept"), .acceptAll, #acceptAll')
        if consent.first.is_visible(timeout=2000):
            consent.first.click()
            time.sleep(1)
    except Exception:
        pass

    # Click to start and type the words
    try:
        page.locator('#typingTest, .word, #words').first.click()
        time.sleep(0.5)

        # Get the words to type
        words = page.evaluate("""
            () => {
                const wordEls = document.querySelectorAll('.word');
                return Array.from(wordEls).slice(0, 20).map(w => {
                    return Array.from(w.querySelectorAll('letter'))
                        .map(l => l.textContent).join('');
                }).filter(w => w.length > 0);
            }
        """)

        if words:
            text = " ".join(words[:15])
            print(f"    Typing: '{text[:50]}...'")
            for char in text:
                page.keyboard.type(char, delay=0)
                time.sleep(random.uniform(0.02, 0.06))  # ~150 WPM
            time.sleep(2)
            print(f"    Typed {len(text)} characters at ~150 WPM!")
        else:
            print("    MonkeyType loaded but couldn't extract words")
    except Exception as e:
        print(f"    Typing test skipped: {e}")


def demo_maps_explore(page):
    """Explore Google Maps — search a place and zoom around."""
    print("\n  [5/6] Google Maps — exploring places...")
    page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
    time.sleep(3)

    # Search for a cool location
    try:
        search = page.locator('#searchboxinput').first
        search.click()
        time.sleep(0.5)

        query = "Taj Mahal, India"
        for char in query:
            page.keyboard.type(char, delay=0)
            time.sleep(random.uniform(0.06, 0.12))

        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(4)

        # Click satellite view if available
        try:
            sat_btn = page.locator('button[aria-label*="Satellite"], button[aria-label*="satellite"]').first
            if sat_btn.is_visible(timeout=2000):
                sat_btn.click()
                time.sleep(2)
        except Exception:
            pass

        smooth_scroll(page, 300)
        time.sleep(2)
        print("    Done! Explored Taj Mahal on Maps")
    except Exception as e:
        print(f"    Maps exploration: {e}")


def demo_hacker_news(page):
    """Browse Hacker News — read top stories like a human."""
    print("\n  [6/6] Hacker News — reading top tech stories...")
    page.goto("https://news.ycombinator.com", wait_until="domcontentloaded")
    time.sleep(2)

    # Read through stories with smooth scrolling
    smooth_scroll(page, 400, steps=30)
    time.sleep(1)

    # Click on a top story
    try:
        story_link = page.locator('.titleline a').first
        title = story_link.text_content()
        print(f"    Opening: '{title[:60]}...'")
        story_link.click()
        time.sleep(3)

        # Read the article
        smooth_scroll(page, 600, steps=35)
        time.sleep(1)
        smooth_scroll(page, 400, steps=25)
        time.sleep(1)
        print("    Done! Read the top story")
    except Exception:
        print("    Browsed Hacker News stories")


def demo_finale(page):
    """Grand finale — inject a custom message on any page."""
    print("\n  FINALE — The ghost leaves a message...")
    page.goto("about:blank")
    time.sleep(0.5)

    page.evaluate("""
        () => {
            document.body.style.background = 'linear-gradient(135deg, #0f0c29, #302b63, #24243e)';
            document.body.style.display = 'flex';
            document.body.style.justifyContent = 'center';
            document.body.style.alignItems = 'center';
            document.body.style.height = '100vh';
            document.body.style.margin = '0';
            document.body.style.fontFamily = '-apple-system, BlinkMacSystemFont, sans-serif';

            const container = document.createElement('div');
            container.style.textAlign = 'center';
            container.style.opacity = '0';
            container.style.transition = 'opacity 1.5s ease';

            container.innerHTML = `
                <h1 style="color: #00d4ff; font-size: 56px; margin-bottom: 10px;
                    text-shadow: 0 0 30px rgba(0,212,255,0.5);">
                    AI Browser Automation
                </h1>
                <p style="color: #a0a0ff; font-size: 28px; margin-bottom: 30px;">
                    Built by Dhruv Tomar — AIwithDhruv
                </p>
                <div style="color: #888; font-size: 18px; line-height: 2;">
                    <p>Google Search &#10003; | Wikipedia &#10003; | GitHub &#10003;</p>
                    <p>Speed Typing &#10003; | Google Maps &#10003; | Hacker News &#10003;</p>
                </div>
                <p style="color: #ffd700; font-size: 22px; margin-top: 30px;
                    animation: pulse 2s infinite;">
                    The browser moves on its own. No human needed.
                </p>
                <style>
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.5; }
                    }
                </style>
            `;

            document.body.appendChild(container);
            setTimeout(() => container.style.opacity = '1', 100);
        }
    """)
    time.sleep(4)


def main():
    print("=" * 60)
    print("  BROWSER AUTOMATION DEMO — Watch the Ghost")
    print("  The browser will do everything by itself!")
    print("=" * 60)
    print("\n  Opening Chrome in 3 seconds...\n")
    time.sleep(3)

    viewport = {"width": 1440, "height": 900}
    browser = BaseBrowser(headless=False, viewport=viewport)
    browser.start()

    try:
        page = browser.page

        demo_google_search(page)
        time.sleep(1)

        demo_wikipedia_speed_read(page)
        time.sleep(1)

        demo_github_explore(page)
        time.sleep(1)

        demo_typing_test(page)
        time.sleep(1)

        demo_maps_explore(page)
        time.sleep(1)

        demo_hacker_news(page)
        time.sleep(1)

        demo_finale(page)

        # Take final screenshot
        screenshot_path = os.path.join(DEMO_DIR, "demo_finale.png")
        page.screenshot(path=screenshot_path)
        print(f"\n  Screenshot saved: {screenshot_path}")

        print("\n" + "=" * 60)
        print("  DEMO COMPLETE! Browser stays open for 30 seconds.")
        print("=" * 60)
        time.sleep(30)

    except KeyboardInterrupt:
        print("\n  Demo stopped by user.")
    finally:
        browser.stop()


if __name__ == "__main__":
    main()
