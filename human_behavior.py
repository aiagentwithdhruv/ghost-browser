#!/usr/bin/env python3
"""
Human behavior simulation engine — makes browser automation look natural.
Anti-detection layer: random delays, realistic typing, smooth scrolling, natural clicks.
"""

import random
import time
import math
import string


class HumanBehavior:
    """
    Simulate human-like interaction patterns for browser automation.
    All methods add realistic randomness to avoid bot detection.
    """

    # Realistic viewport sizes (common screen resolutions)
    VIEWPORTS = [
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1680, "height": 1050},
        {"width": 1280, "height": 800},
    ]

    def __init__(self, action_count=0, break_threshold=None):
        self.action_count = action_count
        self.break_threshold = break_threshold or random.randint(15, 25)
        self.session_start = time.time()

    # ── Delays ──────────────────────────────────────────────

    @staticmethod
    def random_delay(min_sec=0.5, max_sec=3.0):
        """
        Sleep with gaussian distribution (clusters around midpoint).
        More realistic than uniform random — humans have consistent but varied timing.
        """
        mid = (min_sec + max_sec) / 2
        std = (max_sec - min_sec) / 4
        delay = max(min_sec, min(max_sec, random.gauss(mid, std)))
        time.sleep(delay)
        return delay

    @staticmethod
    def micro_delay():
        """Tiny delay between sub-actions (50-300ms)."""
        time.sleep(random.uniform(0.05, 0.3))

    @staticmethod
    def think_delay():
        """Delay simulating reading/thinking (2-6 seconds)."""
        time.sleep(random.uniform(2.0, 6.0))

    @staticmethod
    def between_posts_delay():
        """Delay between processing different posts (3-8 seconds)."""
        time.sleep(random.uniform(3.0, 8.0))

    # ── Typing ──────────────────────────────────────────────

    @staticmethod
    def human_type(page, selector, text, wpm=40, typo_rate=0.05):
        """
        Type text character-by-character with realistic speed and occasional typos.

        Args:
            page: Playwright page object
            selector: CSS selector for input element
            text: Text to type
            wpm: Words per minute (30-60 is realistic)
            typo_rate: Probability of making a typo per character (0.0-0.1)
        """
        element = page.locator(selector)
        element.click()
        HumanBehavior.micro_delay()

        chars_per_sec = wpm * 5 / 60  # Average chars per second
        base_interval = 1.0 / chars_per_sec

        for i, char in enumerate(text):
            # Occasional typo: type wrong char, pause, backspace, type correct
            if random.random() < typo_rate and char.isalpha():
                wrong_char = random.choice(string.ascii_lowercase)
                page.keyboard.type(wrong_char, delay=0)
                time.sleep(random.uniform(0.1, 0.4))  # Notice the mistake
                page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.05, 0.15))

            # Type the correct character
            page.keyboard.type(char, delay=0)

            # Variable delay per character
            interval = base_interval * random.uniform(0.5, 1.8)

            # Longer pause after punctuation and spaces
            if char in ".!?,;:":
                interval += random.uniform(0.2, 0.6)
            elif char == " ":
                interval += random.uniform(0.05, 0.2)
            elif char == "\n":
                interval += random.uniform(0.3, 0.8)

            time.sleep(interval)

    @staticmethod
    def human_type_contenteditable(page, selector, text, wpm=40, typo_rate=0.05):
        """
        Type into contenteditable divs (LinkedIn's Quill/rich-text editor).
        Clicks the element first, then types via keyboard.
        """
        element = page.locator(selector)
        element.click()
        HumanBehavior.micro_delay()

        chars_per_sec = wpm * 5 / 60
        base_interval = 1.0 / chars_per_sec

        for char in text:
            if random.random() < typo_rate and char.isalpha():
                wrong_char = random.choice(string.ascii_lowercase)
                page.keyboard.type(wrong_char, delay=0)
                time.sleep(random.uniform(0.1, 0.4))
                page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.05, 0.15))

            page.keyboard.type(char, delay=0)

            interval = base_interval * random.uniform(0.5, 1.8)
            if char in ".!?,;:":
                interval += random.uniform(0.2, 0.6)
            elif char == " ":
                interval += random.uniform(0.05, 0.2)

            time.sleep(interval)

    # ── Scrolling ───────────────────────────────────────────

    @staticmethod
    def human_scroll(page, direction="down", distance=600):
        """
        Scroll in natural chunks with acceleration/deceleration.
        Humans don't scroll at constant speed — they start slow, speed up, then slow down.
        """
        sign = 1 if direction == "down" else -1
        chunks = random.randint(3, 6)
        total = 0

        for i in range(chunks):
            # Sinusoidal speed curve — slow at start and end, fast in middle
            progress = (i + 0.5) / chunks
            speed_factor = math.sin(progress * math.pi)
            chunk_size = int((distance / chunks) * (0.5 + speed_factor))
            chunk_size = max(30, chunk_size)  # Minimum scroll

            page.evaluate(f"window.scrollBy(0, {sign * chunk_size})")
            total += chunk_size

            # Variable delay between scroll chunks
            time.sleep(random.uniform(0.1, 0.4))

        return total

    @staticmethod
    def scroll_to_element(page, selector, offset=-100):
        """Scroll element into view with some offset (like a human positioning)."""
        page.evaluate(f"""
            () => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            }}
        """)
        time.sleep(random.uniform(0.5, 1.0))

    # ── Clicking ────────────────────────────────────────────

    @staticmethod
    def human_click(page, selector, timeout=5000):
        """
        Click an element with human-like behavior:
        1. Wait for element to be visible
        2. Small delay (noticing the element)
        3. Click with slight position offset
        """
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)

        # Small delay — human noticing the button before clicking
        time.sleep(random.uniform(0.1, 0.4))

        # Click with slight random offset from center
        box = locator.bounding_box()
        if box:
            offset_x = random.uniform(-box["width"] * 0.15, box["width"] * 0.15)
            offset_y = random.uniform(-box["height"] * 0.15, box["height"] * 0.15)
            locator.click(position={"x": box["width"] / 2 + offset_x,
                                     "y": box["height"] / 2 + offset_y})
        else:
            locator.click()

        HumanBehavior.micro_delay()

    # ── Session Management ──────────────────────────────────

    def tick(self):
        """
        Call after each action. Handles break scheduling.
        Returns True if a break was taken.
        """
        self.action_count += 1

        if self.action_count >= self.break_threshold:
            break_duration = random.uniform(30, 120)
            print(
                f"  [Human] Taking a {break_duration:.0f}s break after "
                f"{self.action_count} actions...",
                flush=True,
            )
            time.sleep(break_duration)
            self.action_count = 0
            self.break_threshold = random.randint(15, 25)
            return True
        return False

    @staticmethod
    def should_engage(rate=0.3):
        """Random decision to engage (for batch operations). Returns bool."""
        return random.random() < rate

    @classmethod
    def random_viewport(cls):
        """Return a random realistic viewport size."""
        return random.choice(cls.VIEWPORTS)

    # ── Convenience ─────────────────────────────────────────

    @staticmethod
    def reading_time(text, wpm=200):
        """Estimate how long a human would take to read this text, then wait."""
        words = len(text.split())
        seconds = max(1.5, (words / wpm) * 60)
        seconds *= random.uniform(0.7, 1.3)  # Variance
        time.sleep(seconds)
        return seconds
