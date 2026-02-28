#!/usr/bin/env python3
"""
LinkedInBrowser — LinkedIn-specific browser with engagement + job application methods.
Extends BaseBrowser with human-like behavior for all interactions.

All write actions use human_behavior.py for natural timing, typing, and clicking.
"""

import os
import sys
import json
import time
import random
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser
from human_behavior import HumanBehavior

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass


class LinkedInBrowser(BaseBrowser):
    """
    LinkedIn browser with engagement primitives.
    All actions simulate human behavior (delays, typing, scrolling).
    """

    BASE_URL = "https://www.linkedin.com"

    def __init__(self, li_at=None, headless=True):
        self.li_at = li_at or os.getenv("LINKEDIN_LI_AT")
        if not self.li_at:
            raise ValueError(
                "LINKEDIN_LI_AT not found. Get from DevTools → "
                "Application → Cookies → linkedin.com → li_at"
            )

        viewport = HumanBehavior.random_viewport()
        super().__init__(
            cookies=[{
                "name": "li_at",
                "value": self.li_at,
                "domain": ".linkedin.com",
                "path": "/",
            }],
            headless=headless,
            viewport=viewport,
        )
        self.human = HumanBehavior()

    def _check_auth(self):
        """Verify we're logged in (not redirected to login page)."""
        url = self.page.url
        if "/login" in url or "/checkpoint" in url:
            raise ValueError(
                "LinkedIn redirected to login — li_at cookie expired. "
                "Refresh from DevTools."
            )

    # ── WRITE: Create Post ───────────────────────────────────

    def create_post(self, content, image_path=None):
        """
        Create a new LinkedIn post with human-like typing.

        Args:
            content: Post text (supports newlines)
            image_path: Optional path to image to attach

        Returns:
            True if posted successfully
        """
        print("Creating LinkedIn post...", file=sys.stderr)
        self.goto(f"{self.BASE_URL}/feed/", settle=3)
        self._check_auth()

        # Click "Start a post" button
        start_post_selectors = [
            'button.share-box-feed-entry__trigger',
            'button[aria-label*="Start a post"]',
            '.share-box-feed-entry__trigger',
            'button:has-text("Start a post")',
        ]

        clicked = False
        for sel in start_post_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=3000):
                    HumanBehavior.human_click(self.page, sel)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            print("  Could not find 'Start a post' button", file=sys.stderr)
            return False

        HumanBehavior.random_delay(1.5, 3.0)

        # Find the post editor (contenteditable div in the modal)
        editor_selectors = [
            '.ql-editor[data-placeholder="What do you want to talk about?"]',
            '.ql-editor[contenteditable="true"]',
            '[role="textbox"][aria-label*="post" i]',
            'div[contenteditable="true"][aria-placeholder]',
            '.share-creation-state__text-editor .ql-editor',
        ]

        typed = False
        for sel in editor_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=5000):
                    locator.click()
                    HumanBehavior.micro_delay()

                    # For long posts (>200 chars), insert text directly
                    # (humans write long posts elsewhere and paste too)
                    if len(content) > 200:
                        self.page.keyboard.insert_text(content)
                        HumanBehavior.random_delay(1.0, 2.0)
                    else:
                        HumanBehavior.human_type_contenteditable(
                            self.page, sel, content,
                            wpm=random.randint(40, 55),
                            typo_rate=0.03,
                        )
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            print("  Could not find post editor", file=sys.stderr)
            return False

        HumanBehavior.random_delay(1, 2)

        # Attach image if provided
        has_image = False
        if image_path and os.path.exists(image_path):
            try:
                # Click the image/media button
                media_selectors = [
                    'button[aria-label*="Add a photo"]',
                    'button[aria-label*="photo"]',
                    'button[aria-label*="media"]',
                    'button[aria-label*="image"]',
                ]
                for sel in media_selectors:
                    try:
                        locator = self.page.locator(sel).first
                        if locator.is_visible(timeout=2000):
                            locator.click()
                            HumanBehavior.random_delay(1, 2)
                            break
                    except Exception:
                        continue

                # Upload via file input
                file_input = self.page.locator('input[type="file"]').first
                if file_input:
                    file_input.set_input_files(image_path)
                    print(f"  Image attached: {os.path.basename(image_path)}", file=sys.stderr)
                    has_image = True
                    HumanBehavior.random_delay(3, 5)  # Wait for upload
            except Exception as e:
                print(f"  Image upload failed: {e}", file=sys.stderr)

        # If image was attached, LinkedIn shows an editor with "Next" button
        if has_image:
            next_selectors = [
                'button:has-text("Next")',
                'button[aria-label="Next"]',
                'button.share-box-footer__primary-btn',
            ]
            for sel in next_selectors:
                try:
                    locator = self.page.locator(sel).first
                    if locator.is_visible(timeout=5000):
                        locator.click()
                        HumanBehavior.random_delay(2, 3)
                        break
                except Exception:
                    continue

        # Click Post button
        post_selectors = [
            'button.share-actions__primary-action',
            'button.share-box-footer__primary-btn',
            'button[aria-label="Post"]',
            'button.artdeco-button--primary:has-text("Post")',
        ]

        for sel in post_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=3000) and locator.is_enabled():
                    locator.click()
                    self.human.tick()
                    HumanBehavior.random_delay(2, 4)
                    print("  Post published!", file=sys.stderr)
                    return True
            except Exception:
                continue

        print("  Could not find Post button", file=sys.stderr)
        return False

    # ── READ: Feed ──────────────────────────────────────────

    def get_feed_posts(self, count=10):
        """
        Scroll the LinkedIn feed and extract posts.
        Returns list of dicts: {author, headline, content, post_url, urn, is_liked}
        """
        print(f"Loading LinkedIn feed...", file=sys.stderr)
        self.goto(f"{self.BASE_URL}/feed/", settle=3)
        self._check_auth()

        posts = []
        scroll_rounds = max(3, count // 3)

        for _ in range(scroll_rounds):
            HumanBehavior.human_scroll(self.page, "down", random.randint(400, 800))
            HumanBehavior.random_delay(1.5, 3.0)

        # Extract posts from DOM
        raw_posts = self.evaluate("""
            (maxCount) => {
                const results = [];
                const updates = document.querySelectorAll(
                    '.feed-shared-update-v2, [data-urn*="urn:li:activity"]'
                );

                for (let i = 0; i < Math.min(updates.length, maxCount); i++) {
                    const post = updates[i];
                    const urn = post.getAttribute('data-urn') || '';

                    // Author
                    const authorEl = post.querySelector(
                        '.update-components-actor__name .visually-hidden, ' +
                        '.update-components-actor__title .visually-hidden'
                    );
                    const author = authorEl ? authorEl.textContent.trim() : '';

                    // Headline
                    const headlineEl = post.querySelector(
                        '.update-components-actor__description .visually-hidden, ' +
                        '.update-components-actor__subtitle .visually-hidden'
                    );
                    const headline = headlineEl ? headlineEl.textContent.trim() : '';

                    // Content
                    const contentEl = post.querySelector(
                        '.feed-shared-text .break-words, ' +
                        '.update-components-text .break-words'
                    );
                    const content = contentEl ? contentEl.textContent.trim() : '';

                    // Post URL
                    const linkEl = post.querySelector(
                        'a[href*="/feed/update/"], a[data-urn]'
                    );
                    const postUrl = linkEl ? linkEl.href : '';

                    // Like state
                    const likeBtn = post.querySelector(
                        'button[aria-label*="Like"], ' +
                        'button[aria-label*="like"]'
                    );
                    const isLiked = likeBtn ?
                        (likeBtn.getAttribute('aria-pressed') === 'true') : false;

                    if (content || author) {
                        results.push({
                            urn, author, headline, content: content.substring(0, 500),
                            post_url: postUrl, is_liked: isLiked, index: i
                        });
                    }
                }
                return results;
            }
        """, count)

        print(f"Found {len(raw_posts)} posts in feed", file=sys.stderr)
        return raw_posts

    # ── READ: Comments ──────────────────────────────────────

    def get_post_comments(self, post_url, limit=20):
        """
        Navigate to a post and extract its comments.
        Returns list of dicts: {author, content, timestamp, reply_count}
        """
        print(f"Loading comments for {post_url[:60]}...", file=sys.stderr)
        self.goto(post_url, settle=4)

        # Click "show all comments" if present
        try:
            show_all = self.page.locator(
                'button:has-text("comment"), button:has-text("Comment")'
            ).first
            if show_all.is_visible(timeout=3000):
                HumanBehavior.human_click(self.page, 'button:has-text("comment")')
                HumanBehavior.random_delay(1, 2)
        except Exception:
            pass

        # Scroll to load more comments
        for _ in range(2):
            HumanBehavior.human_scroll(self.page, "down", 400)
            HumanBehavior.random_delay(1, 2)

        comments = self.evaluate("""
            (limit) => {
                const results = [];
                const commentEls = document.querySelectorAll(
                    '.comments-comment-item, ' +
                    '.comments-comment-entity, ' +
                    '[data-urn*="comment"]'
                );

                for (let i = 0; i < Math.min(commentEls.length, limit); i++) {
                    const el = commentEls[i];

                    const authorEl = el.querySelector(
                        '.comments-post-meta__name-text .visually-hidden, ' +
                        '.comments-post-meta__name .hoverable-link-text'
                    );
                    const author = authorEl ? authorEl.textContent.trim() : 'Unknown';

                    const contentEl = el.querySelector(
                        '.comments-comment-item__main-content, ' +
                        '.comments-comment-texteditor .break-words'
                    );
                    const content = contentEl ? contentEl.textContent.trim() : '';

                    const timeEl = el.querySelector('time, .comments-post-meta__time-ago');
                    const timestamp = timeEl ? timeEl.textContent.trim() : '';

                    if (content) {
                        results.push({ author, content: content.substring(0, 300), timestamp, index: i });
                    }
                }
                return results;
            }
        """, limit)

        print(f"Found {len(comments)} comments", file=sys.stderr)
        return comments

    # ── READ: My Post Comments (notifications) ──────────────

    def get_my_post_comments(self, profile_url=None):
        """
        Check your recent posts for new comments.
        Goes to your activity page and checks comment counts.
        """
        url = profile_url or os.getenv(
            "LINKEDIN_PROFILE_URL", f"{self.BASE_URL}/in/aiwithdhruv/"
        )
        activity_url = url.rstrip("/") + "/recent-activity/all/"

        print("Checking your recent posts for comments...", file=sys.stderr)
        self.goto(activity_url, settle=4)

        # Scroll to load posts
        for _ in range(3):
            HumanBehavior.human_scroll(self.page, "down", 500)
            HumanBehavior.random_delay(1, 2)

        posts = self.evaluate("""
            () => {
                const results = [];
                const items = document.querySelectorAll(
                    '.feed-shared-update-v2, [data-urn*="activity"]'
                );

                for (let i = 0; i < Math.min(items.length, 10); i++) {
                    const item = items[i];
                    const urn = item.getAttribute('data-urn') || '';

                    const contentEl = item.querySelector(
                        '.feed-shared-text .break-words, ' +
                        '.update-components-text .break-words'
                    );
                    const content = contentEl ? contentEl.textContent.trim().substring(0, 100) : '';

                    // Engagement numbers
                    const text = item.innerText || '';
                    const commentsMatch = text.match(/(\\d+)\\s*comment/i);
                    const likesMatch = text.match(/(\\d+)\\s*(?:like|reaction)/i);

                    const link = item.querySelector('a[href*="/feed/update/"]');
                    const postUrl = link ? link.href : '';

                    results.push({
                        urn,
                        preview: content,
                        comments: commentsMatch ? parseInt(commentsMatch[1]) : 0,
                        reactions: likesMatch ? parseInt(likesMatch[1]) : 0,
                        post_url: postUrl,
                    });
                }
                return results;
            }
        """)

        posts_with_comments = [p for p in posts if p.get("comments", 0) > 0]
        print(
            f"Found {len(posts)} posts, {len(posts_with_comments)} with comments",
            file=sys.stderr,
        )
        return posts

    # ── WRITE: Like ─────────────────────────────────────────

    def like_post(self, post_index=None, post_urn=None):
        """
        Like a post in the current feed by index or URN.
        Uses human-like click behavior.
        """
        selector = None
        if post_urn:
            selector = f'[data-urn="{post_urn}"] button[aria-label*="Like"]'
        elif post_index is not None:
            # Like the Nth post on the page
            selector = (
                f'.feed-shared-update-v2:nth-of-type({post_index + 1}) '
                f'button[aria-label*="Like"], '
                f'[data-urn]:nth-of-type({post_index + 1}) '
                f'button[aria-label*="Like"]'
            )

        if not selector:
            raise ValueError("Provide post_index or post_urn")

        try:
            HumanBehavior.human_click(self.page, selector)
            self.human.tick()
            print(f"  Liked post", file=sys.stderr)
            return True
        except Exception as e:
            print(f"  Failed to like: {e}", file=sys.stderr)
            return False

    # ── WRITE: Comment ──────────────────────────────────────

    def comment_on_post(self, post_url, comment_text):
        """
        Navigate to a post and leave a comment with human-like typing.

        Args:
            post_url: Full URL to the LinkedIn post
            comment_text: The comment to post
        """
        print(f"Commenting on {post_url[:60]}...", file=sys.stderr)
        self.goto(post_url, settle=4)

        # Click the comment button to open comment box
        try:
            HumanBehavior.human_click(
                self.page,
                'button[aria-label*="Comment"], button[aria-label*="comment"]'
            )
            HumanBehavior.random_delay(1, 2)
        except Exception:
            pass  # Comment box might already be open

        # Find the comment editor (LinkedIn uses contenteditable div)
        editor_selectors = [
            '.ql-editor[data-placeholder*="Add a comment"]',
            '.ql-editor[contenteditable="true"]',
            '[role="textbox"][aria-label*="comment" i]',
            '.comments-comment-box__form .ql-editor',
            'div[contenteditable="true"][aria-placeholder*="comment" i]',
        ]

        typed = False
        for sel in editor_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=3000):
                    # Human-like typing into rich text editor
                    HumanBehavior.human_type_contenteditable(
                        self.page, sel, comment_text, wpm=random.randint(35, 50)
                    )
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            print("  Could not find comment editor", file=sys.stderr)
            return False

        HumanBehavior.random_delay(0.5, 1.5)

        # Click submit/post button
        submit_selectors = [
            'button.comments-comment-box__submit-button',
            'button[type="submit"][aria-label*="Post"]',
            'button:has-text("Post")',
        ]

        for sel in submit_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=2000) and locator.is_enabled():
                    HumanBehavior.human_click(self.page, sel)
                    self.human.tick()
                    print(f"  Comment posted!", file=sys.stderr)
                    HumanBehavior.random_delay(1, 3)
                    return True
            except Exception:
                continue

        print("  Could not find submit button", file=sys.stderr)
        return False

    # ── WRITE: Reply to Comment ─────────────────────────────

    def reply_to_comment(self, post_url, comment_index, reply_text):
        """
        Reply to a specific comment on a post.

        Args:
            post_url: Full URL to the LinkedIn post
            comment_index: 0-based index of the comment to reply to
            reply_text: The reply text
        """
        print(f"Replying to comment #{comment_index}...", file=sys.stderr)
        self.goto(post_url, settle=4)

        # Click reply on the specific comment
        try:
            reply_buttons = self.page.locator(
                'button:has-text("Reply"), button[aria-label*="Reply"]'
            ).all()

            if comment_index < len(reply_buttons):
                reply_buttons[comment_index].click()
                HumanBehavior.random_delay(1, 2)
            else:
                print(f"  Comment #{comment_index} not found (only {len(reply_buttons)} visible)", file=sys.stderr)
                return False
        except Exception as e:
            print(f"  Could not click reply: {e}", file=sys.stderr)
            return False

        # Type reply in the nested comment editor
        editor_selectors = [
            '.ql-editor[contenteditable="true"]',
            '[role="textbox"][contenteditable="true"]',
        ]

        for sel in editor_selectors:
            try:
                # Get the last visible editor (the reply one)
                editors = self.page.locator(sel).all()
                if editors:
                    last_editor = editors[-1]
                    last_editor.click()
                    HumanBehavior.micro_delay()

                    for char in reply_text:
                        self.page.keyboard.type(char, delay=0)
                        time.sleep(random.uniform(0.02, 0.08))

                    HumanBehavior.random_delay(0.5, 1.0)

                    # Submit
                    submit = self.page.locator(
                        'button.comments-comment-box__submit-button, '
                        'button:has-text("Post")'
                    ).last
                    if submit.is_visible() and submit.is_enabled():
                        submit.click()
                        self.human.tick()
                        print(f"  Reply posted!", file=sys.stderr)
                        return True
            except Exception:
                continue

        print("  Could not post reply", file=sys.stderr)
        return False

    # ── WRITE: Connect ──────────────────────────────────────

    def connect_with_note(self, profile_url, note=None):
        """
        Send a connection request, optionally with a personalized note.
        """
        print(f"Visiting {profile_url[:60]}...", file=sys.stderr)
        self.goto(profile_url, settle=3)
        self._check_auth()

        HumanBehavior.think_delay()  # "Reading" the profile

        try:
            # Click Connect button
            HumanBehavior.human_click(
                self.page,
                'button:has-text("Connect"), button[aria-label*="connect" i]'
            )
            HumanBehavior.random_delay(1, 2)

            if note:
                # Click "Add a note"
                try:
                    HumanBehavior.human_click(
                        self.page,
                        'button:has-text("Add a note"), button[aria-label*="note" i]'
                    )
                    HumanBehavior.random_delay(0.5, 1.0)

                    # Type the note
                    HumanBehavior.human_type(
                        self.page,
                        'textarea[name="message"], textarea#custom-message',
                        note,
                        wpm=random.randint(35, 45),
                    )
                    HumanBehavior.random_delay(0.5, 1.0)
                except Exception:
                    pass  # Note field might not be available

            # Click Send
            HumanBehavior.human_click(
                self.page,
                'button:has-text("Send"), button[aria-label*="Send"]'
            )
            self.human.tick()
            print(f"  Connection request sent!", file=sys.stderr)
            return True

        except Exception as e:
            print(f"  Failed to connect: {e}", file=sys.stderr)
            return False

    # ── JOBS: Search ────────────────────────────────────────

    def search_jobs(self, query, location=None, easy_apply_only=False, limit=10):
        """
        Search LinkedIn jobs and extract listings.

        Returns list of dicts: {title, company, location, job_url, is_easy_apply}
        """
        url = f"{self.BASE_URL}/jobs/search/?keywords={query.replace(' ', '%20')}"
        if location:
            url += f"&location={location.replace(' ', '%20')}"
        if easy_apply_only:
            url += "&f_AL=true"

        print(f"Searching jobs: {query}...", file=sys.stderr)
        self.goto(url, settle=4)
        self._check_auth()

        # Scroll to load results
        for _ in range(3):
            HumanBehavior.human_scroll(self.page, "down", 500)
            HumanBehavior.random_delay(1, 2)

        jobs = self.evaluate("""
            (limit) => {
                const results = [];
                const cards = document.querySelectorAll(
                    '.job-card-container, .jobs-search-results__list-item, ' +
                    '[data-job-id], .scaffold-layout__list-item'
                );

                for (let i = 0; i < Math.min(cards.length, limit); i++) {
                    const card = cards[i];

                    const titleEl = card.querySelector(
                        '.job-card-list__title, a.job-card-container__link, ' +
                        '.job-card-list__title--link'
                    );
                    const title = titleEl ? titleEl.textContent.trim() : '';

                    const companyEl = card.querySelector(
                        '.job-card-container__primary-description, ' +
                        '.artdeco-entity-lockup__subtitle'
                    );
                    const company = companyEl ? companyEl.textContent.trim() : '';

                    const locationEl = card.querySelector(
                        '.job-card-container__metadata-wrapper, ' +
                        '.artdeco-entity-lockup__caption'
                    );
                    const location = locationEl ? locationEl.textContent.trim() : '';

                    const link = card.querySelector('a[href*="/jobs/view/"]');
                    const jobUrl = link ? link.href.split('?')[0] : '';

                    const jobId = card.getAttribute('data-job-id') ||
                                  (jobUrl.match(/\\/view\\/(\\d+)/) || [])[1] || '';

                    const easyApply = card.textContent.includes('Easy Apply');

                    if (title) {
                        results.push({
                            title, company, location: location.split('\\n')[0].trim(),
                            job_url: jobUrl, job_id: jobId,
                            is_easy_apply: easyApply, index: i
                        });
                    }
                }
                return results;
            }
        """, limit)

        print(f"Found {len(jobs)} jobs", file=sys.stderr)
        return jobs

    # ── JOBS: Get Details ───────────────────────────────────

    def get_job_details(self, job_url):
        """
        Navigate to a job and extract full details.
        Returns dict: {title, company, location, description, requirements, is_easy_apply}
        """
        print(f"Loading job details...", file=sys.stderr)
        self.goto(job_url, settle=4)

        HumanBehavior.human_scroll(self.page, "down", 300)  # Read the posting
        HumanBehavior.random_delay(1, 2)

        details = self.evaluate("""
            () => {
                const title = document.querySelector(
                    '.jobs-unified-top-card__job-title, h1.t-24, ' +
                    '.job-details-jobs-unified-top-card__job-title'
                );
                const company = document.querySelector(
                    '.jobs-unified-top-card__company-name, ' +
                    '.job-details-jobs-unified-top-card__company-name'
                );
                const location = document.querySelector(
                    '.jobs-unified-top-card__bullet, ' +
                    '.job-details-jobs-unified-top-card__bullet'
                );
                const description = document.querySelector(
                    '.jobs-description__content, .jobs-box__html-content, ' +
                    '#job-details'
                );

                const applyBtn = document.querySelector(
                    'button:has(.jobs-apply-button--top-card), ' +
                    'button[aria-label*="Easy Apply"], ' +
                    '.jobs-apply-button'
                );
                const isEasyApply = applyBtn ?
                    applyBtn.textContent.includes('Easy Apply') : false;

                const externalLink = document.querySelector(
                    'a[href*="externalApply"], button[aria-label*="Apply on company"]'
                );

                return {
                    title: title ? title.textContent.trim() : '',
                    company: company ? company.textContent.trim() : '',
                    location: location ? location.textContent.trim() : '',
                    description: description ? description.textContent.trim().substring(0, 2000) : '',
                    is_easy_apply: isEasyApply,
                    has_external_apply: !!externalLink,
                };
            }
        """)

        return details

    # ── JOBS: Easy Apply ────────────────────────────────────

    def easy_apply(self, job_url, resume_path=None, cover_letter=None, answers=None):
        """
        Apply to a job using LinkedIn's Easy Apply flow.
        Handles multi-step forms with human-like behavior.

        Args:
            job_url: Job listing URL
            resume_path: Path to resume PDF (optional — uses LinkedIn default)
            cover_letter: Cover letter text (optional)
            answers: Dict of field_label -> answer for screening questions
        """
        answers = answers or {}
        print(f"Starting Easy Apply for {job_url[:60]}...", file=sys.stderr)
        self.goto(job_url, settle=4)

        # Click Easy Apply button
        try:
            HumanBehavior.human_click(
                self.page,
                'button[aria-label*="Easy Apply"], '
                'button:has-text("Easy Apply"), '
                '.jobs-apply-button'
            )
            HumanBehavior.random_delay(1, 3)
        except Exception as e:
            print(f"  No Easy Apply button found: {e}", file=sys.stderr)
            return False

        # Handle multi-step form
        max_steps = 8
        for step in range(max_steps):
            HumanBehavior.random_delay(1, 2)

            # Check if we're done (success message)
            try:
                success = self.page.locator(
                    ':has-text("Application sent"), :has-text("application was sent")'
                ).first
                if success.is_visible(timeout=2000):
                    print(f"  Application submitted!", file=sys.stderr)
                    self.human.tick()
                    return True
            except Exception:
                pass

            # Upload resume if file input exists and path provided
            if resume_path and os.path.exists(resume_path):
                try:
                    file_input = self.page.locator('input[type="file"]').first
                    if file_input.is_visible(timeout=1000):
                        file_input.set_input_files(resume_path)
                        HumanBehavior.random_delay(1, 2)
                except Exception:
                    pass

            # Fill cover letter if textarea exists
            if cover_letter:
                try:
                    textarea = self.page.locator(
                        'textarea[aria-label*="cover letter" i], '
                        'textarea[name*="cover" i], '
                        'label:has-text("cover letter") + textarea'
                    ).first
                    if textarea.is_visible(timeout=1000):
                        HumanBehavior.human_type(
                            self.page,
                            'textarea[aria-label*="cover letter" i]',
                            cover_letter,
                            wpm=random.randint(40, 55),
                        )
                except Exception:
                    pass

            # Fill screening questions
            self._fill_screening_questions(answers)

            # Click Next / Review / Submit
            next_clicked = False
            for btn_text in ["Next", "Review", "Submit application", "Submit", "Continue"]:
                try:
                    btn = self.page.locator(f'button:has-text("{btn_text}")').first
                    if btn.is_visible(timeout=1000) and btn.is_enabled():
                        HumanBehavior.human_click(
                            self.page, f'button:has-text("{btn_text}")'
                        )
                        next_clicked = True
                        break
                except Exception:
                    continue

            if not next_clicked:
                # Try generic footer button
                try:
                    footer_btn = self.page.locator(
                        '.artdeco-modal__actionbar button[aria-label*="next" i], '
                        '.artdeco-modal__actionbar button[aria-label*="submit" i]'
                    ).first
                    if footer_btn.is_visible(timeout=1000):
                        footer_btn.click()
                except Exception:
                    print(f"  Stuck at step {step + 1}, no next button found", file=sys.stderr)
                    # Screenshot for debugging
                    self.screenshot(
                        os.path.join(os.path.dirname(__file__), "stats",
                                     f"apply_stuck_step{step + 1}.png")
                    )
                    return False

        print("  Max steps reached without success", file=sys.stderr)
        return False

    def _fill_screening_questions(self, answers):
        """Fill common screening question fields in Easy Apply forms."""
        # Text inputs
        try:
            inputs = self.page.locator(
                '.jobs-easy-apply-form-section__grouping input[type="text"], '
                '.jobs-easy-apply-form-section__grouping select'
            ).all()

            for inp in inputs:
                try:
                    label = inp.evaluate(
                        """el => {
                            const label = el.closest('.jobs-easy-apply-form-section__grouping')
                                ?.querySelector('label');
                            return label ? label.textContent.trim() : '';
                        }"""
                    )
                    if label:
                        for key, value in answers.items():
                            if key.lower() in label.lower():
                                tag = inp.evaluate("el => el.tagName")
                                if tag == "SELECT":
                                    inp.select_option(label=value)
                                else:
                                    inp.fill(value)
                                HumanBehavior.micro_delay()
                                break
                except Exception:
                    continue
        except Exception:
            pass

        # Radio buttons (Yes/No questions)
        try:
            radios = self.page.locator(
                'fieldset[data-test-form-builder-radio-button-form-component]'
            ).all()
            for fieldset in radios:
                try:
                    legend = fieldset.locator("legend, span.visually-hidden").first
                    question = legend.text_content().strip() if legend else ""

                    # Default to "Yes" for common questions
                    for key, value in answers.items():
                        if key.lower() in question.lower():
                            option = fieldset.locator(f'label:has-text("{value}")').first
                            if option.is_visible():
                                option.click()
                            break
                    else:
                        # Auto-select "Yes" if no specific answer
                        yes_option = fieldset.locator('label:has-text("Yes")').first
                        if yes_option.is_visible():
                            yes_option.click()
                except Exception:
                    continue
        except Exception:
            pass

    # ── JOBS: External Apply ────────────────────────────────

    def external_apply(self, job_url, form_data=None):
        """
        Handle external job application — navigates to company site.
        Attempts to fill common fields. Screenshots if stuck.

        Args:
            job_url: LinkedIn job URL (will redirect to company site)
            form_data: Dict with keys like name, email, phone, resume_path, cover_letter
        """
        form_data = form_data or {}
        print(f"External apply: {job_url[:60]}...", file=sys.stderr)
        self.goto(job_url, settle=3)

        # Click the external apply button
        try:
            HumanBehavior.human_click(
                self.page,
                'button:has-text("Apply"), a:has-text("Apply on company"), '
                'a[href*="externalApply"]'
            )
            HumanBehavior.random_delay(2, 4)
        except Exception as e:
            print(f"  No external apply button: {e}", file=sys.stderr)
            return False

        # Wait for new tab or redirect
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        HumanBehavior.random_delay(2, 3)
        current_url = self.page.url
        print(f"  Redirected to: {current_url[:80]}", file=sys.stderr)

        # Attempt to fill common form fields
        field_map = {
            "name": ['input[name*="name" i]', 'input[placeholder*="name" i]',
                      'input[aria-label*="name" i]'],
            "first_name": ['input[name*="first" i]', 'input[id*="first" i]'],
            "last_name": ['input[name*="last" i]', 'input[id*="last" i]'],
            "email": ['input[type="email"]', 'input[name*="email" i]',
                       'input[placeholder*="email" i]'],
            "phone": ['input[type="tel"]', 'input[name*="phone" i]',
                       'input[placeholder*="phone" i]'],
            "linkedin": ['input[name*="linkedin" i]', 'input[placeholder*="linkedin" i]'],
        }

        filled = 0
        for field, selectors in field_map.items():
            value = form_data.get(field)
            if not value:
                continue
            for sel in selectors:
                try:
                    locator = self.page.locator(sel).first
                    if locator.is_visible(timeout=1000):
                        HumanBehavior.human_type(
                            self.page, sel, value, wpm=random.randint(35, 50)
                        )
                        filled += 1
                        break
                except Exception:
                    continue

        # Upload resume
        resume = form_data.get("resume_path")
        if resume and os.path.exists(resume):
            try:
                file_input = self.page.locator('input[type="file"]').first
                if file_input.is_visible(timeout=2000):
                    file_input.set_input_files(resume)
                    filled += 1
            except Exception:
                pass

        # Fill cover letter
        cover = form_data.get("cover_letter")
        if cover:
            try:
                textarea = self.page.locator(
                    'textarea[name*="cover" i], textarea[placeholder*="cover" i], '
                    'textarea[aria-label*="cover" i]'
                ).first
                if textarea.is_visible(timeout=1000):
                    HumanBehavior.human_type(
                        self.page,
                        'textarea[name*="cover" i]',
                        cover,
                        wpm=random.randint(40, 55),
                    )
                    filled += 1
            except Exception:
                pass

        # Screenshot the current state
        screenshot_path = os.path.join(
            os.path.dirname(__file__), "stats",
            f"external_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        self.screenshot(screenshot_path, full_page=True)
        print(f"  Filled {filled} fields. Screenshot: {screenshot_path}", file=sys.stderr)
        print(f"  Review and submit manually if needed.", file=sys.stderr)

        self.human.tick()
        return {"filled": filled, "screenshot": screenshot_path, "url": current_url}
