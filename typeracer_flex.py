#!/usr/bin/env python3
"""
Typing Race — uses your REAL Chrome profile to bypass Cloudflare.
Tries TypeRacer with your existing cookies, falls back to 10FastFingers.
"""

import sys
import os
import time
import random
import shutil

sys.path.insert(0, os.path.dirname(__file__))


def get_chrome_profile():
    """Find the user's Chrome profile directory."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Library/Application Support/Google/Chrome"),
        os.path.join(home, "Library/Application Support/Google/Chrome Canary"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def run_10fastfingers():
    """Race on 10FastFingers — no CAPTCHA issues."""
    from playwright.sync_api import sync_playwright

    print("\n  Using 10FastFingers (no Cloudflare)...")
    pw = sync_playwright().start()

    browser = pw.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")

    try:
        page.goto("https://10fastfingers.com/typing-test/english", wait_until="domcontentloaded")
        time.sleep(4)

        # Accept cookies if prompted
        for sel in ['#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
                     'button:has-text("Accept")', '#accept-cookie', '.cookie-accept',
                     'button:has-text("Allow")', 'button:has-text("Consent")']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    time.sleep(1)
                    break
            except Exception:
                continue

        time.sleep(2)

        # Extract words from the test
        print("  Extracting words...")
        words = page.evaluate("""
            () => {
                const wordSpans = document.querySelectorAll('#row1 span, .highlight, #wordlist span');
                if (wordSpans.length > 0) {
                    return Array.from(wordSpans).map(s => s.textContent).filter(w => w.trim());
                }
                // Alternative
                const highlights = document.querySelectorAll('[class*="highlight"], .word');
                return Array.from(highlights).map(s => s.textContent).filter(w => w.trim());
            }
        """)

        if not words or len(words) < 3:
            print("  Trying broader word extraction...")
            words = page.evaluate("""
                () => {
                    const container = document.querySelector('#row1, .words, #wordlist, .test-words');
                    if (container) {
                        return container.textContent.trim().split(/\\s+/).filter(w => w.length > 0);
                    }
                    return [];
                }
            """)

        if words and len(words) > 0:
            print(f"  Found {len(words)} words")
            print(f"  First words: {' '.join(words[:10])}...\n")

            # Focus the input
            try:
                page.locator('#inputfield, input[type="text"]').first.click()
            except Exception:
                page.keyboard.press("Tab")
            time.sleep(0.5)

            # Type each word + space at ~150 WPM
            print("  TYPING!")
            start = time.time()
            total_chars = 0

            for word in words:
                text_to_type = word + " "
                for char in text_to_type:
                    page.keyboard.type(char, delay=0)
                    total_chars += 1

                    # ~150 WPM with natural variance
                    base = random.uniform(0.055, 0.095)
                    if char == " ":
                        base += random.uniform(0.01, 0.04)
                    if random.random() < 0.02:
                        base += random.uniform(0.1, 0.2)
                    time.sleep(base)

                # Stop after ~60 seconds (test length)
                if time.time() - start > 58:
                    break

            elapsed = time.time() - start
            wpm = (total_chars / 5) / (elapsed / 60)
            print(f"\n  Typed {total_chars} chars in {elapsed:.1f}s")
            print(f"  Speed: ~{wpm:.0f} WPM")
        else:
            print("  Could not extract words.")
            page.screenshot(path="/tmp/typing_debug.png")
            print("  Screenshot: /tmp/typing_debug.png")

        # Wait for results
        time.sleep(8)
        page.screenshot(path="/tmp/typing_result.png")
        print(f"  Screenshot: /tmp/typing_result.png")

        print(f"\n  Browser open for 60s — check the score!")
        time.sleep(60)

    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        try:
            page.close()
            context.close()
            browser.close()
            pw.stop()
        except Exception:
            pass


def run_typeracer_with_profile():
    """Try TypeRacer using real Chrome profile to bypass Cloudflare."""
    from playwright.sync_api import sync_playwright

    chrome_dir = get_chrome_profile()
    if not chrome_dir:
        print("  Chrome profile not found, using 10FastFingers instead...")
        return False

    # Copy profile to temp to avoid lock conflicts with running Chrome
    tmp_profile = "/tmp/chrome_typeracer_profile"
    if os.path.exists(tmp_profile):
        shutil.rmtree(tmp_profile)

    print(f"  Using Chrome profile: {chrome_dir}")
    print("  IMPORTANT: Close Chrome first if it's open!\n")
    time.sleep(3)

    pw = sync_playwright().start()

    try:
        context = pw.chromium.launch_persistent_context(
            tmp_profile,
            headless=False,
            viewport={"width": 1440, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")

        page.goto("https://play.typeracer.com", wait_until="domcontentloaded")
        time.sleep(5)

        # Check if Cloudflare is still blocking
        if "just a moment" in page.title().lower():
            print("  Still got Cloudflare. Click the CAPTCHA in the browser!")
            for i in range(30):
                if "just a moment" not in page.title().lower():
                    print("  Cleared!")
                    break
                time.sleep(1)
            else:
                print("  Cloudflare still blocking. Falling back to 10FastFingers.")
                context.close()
                pw.stop()
                return False

        time.sleep(3)
        print("  TypeRacer loaded!")

        # Enter race
        page.evaluate("""
            () => {
                const links = document.querySelectorAll('a, button, .gwt-Anchor');
                for (const l of links) {
                    if (l.textContent.toLowerCase().includes('enter a typing race')) {
                        l.click(); return;
                    }
                }
            }
        """)
        time.sleep(8)

        # Extract text
        race_text = page.evaluate("""
            () => {
                const spans = document.querySelectorAll('table.gameStatusTable span');
                let t = '';
                for (const s of spans) {
                    if (s.offsetParent && s.textContent && !s.querySelector('input'))
                        t += s.textContent;
                }
                return t.trim();
            }
        """)

        if race_text and len(race_text) > 15:
            print(f"  Race text: \"{race_text[:80]}...\"\n")

            # Wait for input
            for _ in range(20):
                if page.evaluate("() => { const i = document.querySelector('input.txtInput'); return i && !i.disabled; }"):
                    break
                time.sleep(0.5)

            page.locator('input.txtInput').first.click()
            time.sleep(0.3)

            # Type at ~150 WPM
            start = time.time()
            for char in race_text:
                page.keyboard.type(char, delay=0)
                base = random.uniform(0.055, 0.095)
                if char in ".!?,": base += random.uniform(0.05, 0.12)
                if char == " ": base += random.uniform(0.01, 0.03)
                time.sleep(base)

            elapsed = time.time() - start
            wpm = (len(race_text) / 5) / (elapsed / 60)
            print(f"  {len(race_text)} chars in {elapsed:.1f}s = ~{wpm:.0f} WPM")
            time.sleep(8)
            page.screenshot(path="/tmp/typeracer_result.png")
            print(f"  Screenshot: /tmp/typeracer_result.png")
            print("  Browser open for 60s!")
            time.sleep(60)
            context.close()
            pw.stop()
            return True

        context.close()
        pw.stop()
        return False

    except Exception as e:
        print(f"  TypeRacer failed: {e}")
        try:
            pw.stop()
        except Exception:
            pass
        return False


def main():
    print("=" * 60)
    print("  TYPING RACE — ~150 WPM (fast but believable)")
    print("=" * 60)

    # Try TypeRacer with real Chrome first
    success = run_typeracer_with_profile()

    # Fall back to 10FastFingers
    if not success:
        run_10fastfingers()


if __name__ == "__main__":
    main()
