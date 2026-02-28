#!/usr/bin/env python3
"""MonkeyType speed demon — 15 second test, superhuman speed."""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser


def main():
    print("Opening MonkeyType — 15 sec test, SUPERFAST mode...\n")

    browser = BaseBrowser(headless=False, viewport={"width": 1440, "height": 900})
    browser.start()
    page = browser.page

    try:
        page.goto("https://monkeytype.com", wait_until="domcontentloaded")
        time.sleep(4)

        # Dismiss cookie/popup
        for sel in ['button:has-text("Accept")', '.acceptAll', '#acceptAll',
                     'button:has-text("Reject")', '.rejectAll']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    time.sleep(0.5)
                    break
            except Exception:
                continue

        time.sleep(1)

        # Switch to 15 second mode
        print("  Setting 15 second mode...")
        try:
            # Click "time" mode button first
            time_btn = page.locator('button:has-text("time")').first
            if time_btn.is_visible(timeout=2000):
                time_btn.click()
                time.sleep(0.5)

            # Click "15" duration
            fifteen_btn = page.locator('button:has-text("15")').first
            if fifteen_btn.is_visible(timeout=2000):
                fifteen_btn.click()
                time.sleep(1)
                print("  15 second mode set!")
        except Exception as e:
            print(f"  Could not set 15s mode: {e}")

        # Focus the typing area
        try:
            page.locator('#typingTest').first.click()
            time.sleep(0.5)
        except Exception:
            page.locator('.word').first.click()
            time.sleep(0.5)

        # Get words and TYPE FAST
        print("  GO GO GO!\n")

        words = page.evaluate("""
            () => {
                const wordEls = document.querySelectorAll('.word');
                return Array.from(wordEls).slice(0, 100).map(w => {
                    return Array.from(w.querySelectorAll('letter'))
                        .map(l => l.textContent).join('');
                }).filter(w => w.length > 0);
            }
        """)

        if words:
            text = " ".join(words)
            start = time.time()
            chars_typed = 0

            for char in text:
                # Stop after ~16s (give results time to show)
                if time.time() - start > 16:
                    break
                page.keyboard.type(char, delay=0)
                chars_typed += 1
                # BLAZING: 10-25ms per char = ~300-600 WPM
                time.sleep(random.uniform(0.010, 0.025))

            elapsed = time.time() - start
            wpm = (chars_typed / 5) / (elapsed / 60)
            print(f"  Typed {chars_typed} chars in {elapsed:.1f}s")
            print(f"  Speed: ~{wpm:.0f} WPM")

        # Wait for results to appear
        time.sleep(6)

        # Screenshot the results
        page.screenshot(path="/tmp/monkeytype_15s.png")
        print("\n  Screenshot: /tmp/monkeytype_15s.png")

        print("\n  Browser stays open for 30s — show them the score!")
        time.sleep(30)

    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        browser.stop()


if __name__ == "__main__":
    main()
