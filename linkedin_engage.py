#!/usr/bin/env python3
"""
LinkedIn Engagement CLI — human-like LinkedIn automation.

Commands:
    feed       — Scroll feed, show posts, offer to like/comment
    comments   — Check your posts for comments, offer to reply
    engage     — Batch like + comment on feed posts (AI-generated)
    apply      — Search + apply to jobs (Easy Apply + External)
    connect    — Send connection requests with notes
    post       — Create a LinkedIn post with optional image

Usage:
    python3 linkedin_engage.py feed --visible
    python3 linkedin_engage.py comments --visible
    python3 linkedin_engage.py engage --count 3 --visible
    python3 linkedin_engage.py apply --query "AI engineer" --location "Remote" --visible
    python3 linkedin_engage.py connect --profile "https://linkedin.com/in/..." --note "Hey!"
    python3 linkedin_engage.py post --text-file post.txt --image photo.jpg --visible
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from linkedin_browser import LinkedInBrowser
from human_behavior import HumanBehavior

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

STATS_DIR = os.path.join(os.path.dirname(__file__), "stats")
os.makedirs(STATS_DIR, exist_ok=True)

# ── AI Comment Generation ───────────────────────────────────

BRAND_SYSTEM_PROMPT = """You are Dhruv Tomar (AIwithDhruv), an Applied AI Engineer.
Your tone: 40% witty realism, 30% strategic clarity, 20% motivational, 10% personal.
Write SHORT LinkedIn comments (1-3 sentences max).
Be genuine, add value, share a relevant insight or ask a smart question.
Never be generic ("Great post!"). Never use emojis excessively.
Sound like a real person who actually read the post and has something to add."""


def generate_ai_comment(post_content, post_author=""):
    """Generate an AI comment using OpenAI or fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import requests
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": BRAND_SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Write a comment on this LinkedIn post by {post_author}:\n\n"
                        f"{post_content[:500]}\n\n"
                        "Comment (1-3 sentences, add genuine value):"
                    )},
                ],
                "max_tokens": 150,
                "temperature": 0.8,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  AI generation failed: {e}", file=sys.stderr)
        return None


def generate_ai_cover_letter(job_details):
    """Generate an AI cover letter using OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import requests
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": (
                        "You are Dhruv Tomar, an Applied AI Engineer with 2+ years experience "
                        "in LangGraph, Multi-Agent Orchestration, Voice AI, RAG systems, "
                        "n8n automation (210+ workflows), and full-stack AI development. "
                        "Write a concise, compelling cover letter (150 words max). "
                        "Focus on relevant experience and specific value you'd bring."
                    )},
                    {"role": "user", "content": (
                        f"Write a cover letter for:\n\n"
                        f"Title: {job_details.get('title', '')}\n"
                        f"Company: {job_details.get('company', '')}\n"
                        f"Description: {job_details.get('description', '')[:500]}\n\n"
                        "Cover letter (150 words max):"
                    )},
                ],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  Cover letter generation failed: {e}", file=sys.stderr)
        return None


def prompt_user(message, default="y"):
    """Ask user for confirmation."""
    try:
        resp = input(f"{message} [{default}]: ").strip().lower()
        return resp or default
    except (EOFError, KeyboardInterrupt):
        return "n"


def log_action(action_type, details):
    """Log engagement actions to stats/engagement_log.json."""
    log_file = os.path.join(STATS_DIR, "engagement_log.json")
    log = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            log = json.load(f)

    log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action_type,
        **details,
    })

    with open(log_file, "w") as f:
        json.dump(log, f, indent=2)


# ── Commands ────────────────────────────────────────────────

def cmd_feed(args):
    """Scroll feed, show posts, offer to like/comment."""
    browser = LinkedInBrowser(headless=not args.visible)
    browser.start()

    try:
        posts = browser.get_feed_posts(count=args.count)

        for i, post in enumerate(posts):
            print(f"\n{'='*60}")
            print(f"[{i+1}] {post['author']}")
            if post.get('headline'):
                print(f"    {post['headline'][:80]}")
            print(f"    {post['content'][:200]}...")
            print(f"    Liked: {'Yes' if post['is_liked'] else 'No'}")
            if post.get('post_url'):
                print(f"    URL: {post['post_url'][:80]}")

            if not args.auto:
                action = prompt_user("  Action? (l)ike / (c)omment / (s)kip / (q)uit", "s")
            else:
                action = "s"

            if action == "l" and not post["is_liked"]:
                browser.like_post(post_index=post["index"])
                log_action("like", {"author": post["author"], "url": post.get("post_url", "")})

            elif action == "c":
                comment = generate_ai_comment(post["content"], post["author"])
                if comment:
                    print(f"\n  AI comment: {comment}")
                    confirm = prompt_user("  Post this comment? (y/n/e)dit", "y")
                    if confirm == "e":
                        comment = input("  Your comment: ").strip()
                        confirm = "y"
                    if confirm == "y" and post.get("post_url"):
                        browser.comment_on_post(post["post_url"], comment)
                        log_action("comment", {
                            "author": post["author"],
                            "url": post.get("post_url", ""),
                            "comment": comment,
                        })
                else:
                    comment = input("  Type your comment: ").strip()
                    if comment and post.get("post_url"):
                        browser.comment_on_post(post["post_url"], comment)
                        browser.goto("https://www.linkedin.com/feed/", settle=3)

            elif action == "q":
                break

            HumanBehavior.between_posts_delay()

    finally:
        browser.stop()


def cmd_comments(args):
    """Check your posts for comments, offer to reply."""
    browser = LinkedInBrowser(headless=not args.visible)
    browser.start()

    try:
        posts = browser.get_my_post_comments()

        for post in posts:
            if post.get("comments", 0) == 0:
                continue

            print(f"\n{'='*60}")
            print(f"  Post: {post['preview'][:100]}...")
            print(f"  Reactions: {post.get('reactions', 0)} | Comments: {post.get('comments', 0)}")

            if not post.get("post_url"):
                continue

            view = prompt_user("  View comments? (y/n)", "y")
            if view != "y":
                continue

            comments = browser.get_post_comments(post["post_url"])
            for j, comment in enumerate(comments):
                print(f"\n    [{j+1}] {comment['author']} ({comment.get('timestamp', '')}):")
                print(f"        {comment['content'][:200]}")

                action = prompt_user("    (r)eply / (s)kip", "s")
                if action == "r":
                    reply = generate_ai_comment(
                        f"Replying to: {comment['content']}", comment["author"]
                    )
                    if reply:
                        print(f"\n    AI reply: {reply}")
                        confirm = prompt_user("    Post this? (y/n/e)dit", "y")
                        if confirm == "e":
                            reply = input("    Your reply: ").strip()
                            confirm = "y"
                    else:
                        reply = input("    Your reply: ").strip()
                        confirm = "y"

                    if confirm == "y" and reply:
                        browser.reply_to_comment(post["post_url"], j, reply)
                        log_action("reply", {
                            "post_url": post["post_url"],
                            "to": comment["author"],
                            "reply": reply,
                        })

            # Navigate back to activity page
            browser.goto(
                os.getenv("LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/aiwithdhruv/")
                .rstrip("/") + "/recent-activity/all/",
                settle=3,
            )

    finally:
        browser.stop()


def cmd_engage(args):
    """Batch engagement — like + comment on N posts with human-like pacing."""
    import random as _rand

    browser = LinkedInBrowser(headless=not args.visible)
    browser.start()

    try:
        posts = browser.get_feed_posts(count=args.count * 3)  # Get extra for filtering
        engaged = 0
        skipped = 0

        for post in posts:
            if engaged >= args.count:
                break

            if post["is_liked"]:
                continue

            # ── Human behavior: don't engage with every single post ──
            # Skip ~20% of posts randomly (humans scroll past some)
            if _rand.random() < 0.2 and engaged > 0:
                skipped += 1
                print(f"  [scrolled past: {post['author'][:30]}]", file=sys.stderr)
                HumanBehavior.random_delay(1.0, 2.5)  # Quick scroll past
                continue

            print(f"\n{'='*60}")
            print(f"[{engaged+1}/{args.count}] {post['author']}")
            print(f"    {post['content'][:200]}...")

            # ── Human behavior: "read" the post before engaging ──
            word_count = len(post.get("content", "").split())
            read_time = max(2.0, min(8.0, word_count / 200 * 60))  # ~200 WPM reading
            read_time *= _rand.uniform(0.7, 1.4)  # Natural variance
            print(f"  [reading {read_time:.1f}s...]", file=sys.stderr)
            import time as _time
            _time.sleep(read_time)

            # Like
            browser.like_post(post_index=post["index"])
            log_action("like", {"author": post["author"]})

            # ── Human behavior: pause after liking (like absorbing the action) ──
            HumanBehavior.random_delay(1.0, 3.0)

            # Comment (if AI available and not like-only)
            if not args.like_only:
                # Humans don't comment on every post they like — ~60% comment rate
                should_comment = _rand.random() < 0.6
                if should_comment:
                    comment = generate_ai_comment(post["content"], post["author"])
                    if comment:
                        print(f"  AI comment: {comment}")
                        confirm = prompt_user("  Post? (y/n/e)dit", "y")
                        if confirm == "e":
                            comment = input("  Your comment: ").strip()
                            confirm = "y"
                        if confirm == "y" and post.get("post_url"):
                            browser.comment_on_post(post["post_url"], comment)
                            log_action("comment", {
                                "author": post["author"],
                                "comment": comment,
                            })
                            # Navigate back to feed with a natural delay
                            HumanBehavior.random_delay(2.0, 4.0)
                            browser.goto("https://www.linkedin.com/feed/", settle=3)
                else:
                    print(f"  [liked only — moving on]", file=sys.stderr)

            engaged += 1

            # ── Human behavior: variable delay between posts ──
            # Longer pauses feel natural — 5-15 seconds between engagements
            between_delay = _rand.uniform(5.0, 15.0)
            print(f"  [waiting {between_delay:.0f}s before next...]", file=sys.stderr)
            _time.sleep(between_delay)

            # ── Human behavior: occasional idle scroll (just browsing, not engaging) ──
            if _rand.random() < 0.3:
                idle_scrolls = _rand.randint(1, 3)
                print(f"  [idle scrolling {idle_scrolls}x...]", file=sys.stderr)
                for _ in range(idle_scrolls):
                    HumanBehavior.human_scroll(browser.page, "down", _rand.randint(200, 500))
                    HumanBehavior.random_delay(1.5, 4.0)

        print(f"\nEngaged with {engaged} posts (skipped {skipped})")

    finally:
        browser.stop()


def cmd_apply(args):
    """Search + apply to jobs."""
    browser = LinkedInBrowser(headless=not args.visible)
    browser.start()

    applications = []
    try:
        jobs = browser.search_jobs(
            args.query,
            location=args.location,
            easy_apply_only=args.easy_apply_only,
            limit=args.count,
        )

        for i, job in enumerate(jobs):
            print(f"\n{'='*60}")
            print(f"[{i+1}/{len(jobs)}] {job['title']}")
            print(f"    Company: {job['company']}")
            print(f"    Location: {job['location']}")
            print(f"    Easy Apply: {'Yes' if job['is_easy_apply'] else 'No (External)'}")

            action = prompt_user("  (a)pply / (d)etails / (s)kip / (q)uit", "s")

            if action == "q":
                break

            if action == "d":
                if job.get("job_url"):
                    details = browser.get_job_details(job["job_url"])
                    print(f"\n    Description: {details.get('description', '')[:300]}...")
                    action = prompt_user("  (a)pply / (s)kip", "s")

            if action == "a" and job.get("job_url"):
                # Generate cover letter
                details = browser.get_job_details(job["job_url"]) if action != "d" else details
                cover_letter = generate_ai_cover_letter(details) if not args.no_cover else None

                if cover_letter:
                    print(f"\n  Cover letter:\n  {cover_letter[:200]}...")
                    confirm = prompt_user("  Use this? (y/n/e)dit", "y")
                    if confirm == "e":
                        cover_letter = input("  Your cover letter: ").strip()
                    elif confirm != "y":
                        cover_letter = None

                result = None
                if job["is_easy_apply"]:
                    success = browser.easy_apply(
                        job["job_url"],
                        resume_path=args.resume,
                        cover_letter=cover_letter,
                    )
                    result = {"type": "easy_apply", "success": success}
                else:
                    result = browser.external_apply(
                        job["job_url"],
                        form_data={
                            "name": "Dhruv Tomar",
                            "first_name": "Dhruv",
                            "last_name": "Tomar",
                            "email": os.getenv("EMAIL", ""),
                            "phone": os.getenv("PHONE", ""),
                            "linkedin": "https://www.linkedin.com/in/aiwithdhruv/",
                            "resume_path": args.resume,
                            "cover_letter": cover_letter,
                        },
                    )

                app_record = {
                    "title": job["title"],
                    "company": job["company"],
                    "url": job.get("job_url", ""),
                    **(result or {}),
                }
                applications.append(app_record)
                log_action("job_apply", app_record)

                # Navigate back to search results
                browser.goto(
                    f"https://www.linkedin.com/jobs/search/?keywords={args.query.replace(' ', '%20')}",
                    settle=3,
                )

            HumanBehavior.between_posts_delay()

        # Save applications log
        if applications:
            apps_file = os.path.join(STATS_DIR, "job_applications.json")
            existing = []
            if os.path.exists(apps_file):
                with open(apps_file, "r") as f:
                    existing = json.load(f)
            existing.extend(applications)
            with open(apps_file, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"\n{len(applications)} applications logged to {apps_file}")

    finally:
        browser.stop()


def cmd_connect(args):
    """Send connection request with note."""
    browser = LinkedInBrowser(headless=not args.visible)
    browser.start()

    try:
        if args.profile:
            profiles = [args.profile]
        elif args.profiles_file:
            with open(args.profiles_file, "r") as f:
                profiles = [line.strip() for line in f if line.strip()]
        else:
            print("Provide --profile URL or --profiles-file", file=sys.stderr)
            return

        for profile in profiles:
            note = args.note
            if not note and not args.no_note:
                note = input(f"Note for {profile}: ").strip() or None

            browser.connect_with_note(profile, note=note)
            log_action("connect", {"profile": profile, "note": note})
            HumanBehavior.between_posts_delay()

    finally:
        browser.stop()


# ── Post ────────────────────────────────────────────────────

def cmd_post(args):
    """Create a LinkedIn post with optional image."""
    # Get post text
    if args.text_file:
        with open(args.text_file) as f:
            content = f.read().strip()
    elif args.text:
        content = args.text
    else:
        print("Enter post text (Ctrl+D when done):")
        content = sys.stdin.read().strip()

    if not content:
        print("No content provided.")
        return

    print(f"\n--- Post Preview ---")
    print(content[:200] + ("..." if len(content) > 200 else ""))
    if args.image:
        print(f"Image: {args.image}")
    print("---")

    confirm = input("\nPost this? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    headless = not args.visible
    browser = LinkedInBrowser(headless=headless)
    browser.start()
    try:
        success = browser.create_post(content, image_path=args.image)
        if success:
            log_action("post", {
                "content_preview": content[:100],
                "has_image": bool(args.image),
            })
            print("\nPost published successfully!")
        else:
            print("\nPost failed — check browser if visible.")
    finally:
        browser.stop()


# ── Main ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Engagement CLI — human-like automation"
    )
    parser.add_argument("--visible", action="store_true", help="Show browser window")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # feed
    p_feed = sub.add_parser("feed", help="Scroll feed, like/comment on posts")
    p_feed.add_argument("--count", type=int, default=10, help="Posts to load")
    p_feed.add_argument("--auto", action="store_true", help="Auto-scroll without prompts")

    # comments
    p_comments = sub.add_parser("comments", help="Check your posts for comments")

    # engage
    p_engage = sub.add_parser("engage", help="Batch like + comment")
    p_engage.add_argument("--count", type=int, default=5, help="Posts to engage with")
    p_engage.add_argument("--like-only", action="store_true", help="Only like, don't comment")

    # apply
    p_apply = sub.add_parser("apply", help="Search + apply to jobs")
    p_apply.add_argument("--query", required=True, help="Job search query")
    p_apply.add_argument("--location", help="Job location filter")
    p_apply.add_argument("--count", type=int, default=10, help="Jobs to show")
    p_apply.add_argument("--easy-apply-only", action="store_true", help="Only Easy Apply jobs")
    p_apply.add_argument("--resume", help="Path to resume PDF")
    p_apply.add_argument("--no-cover", action="store_true", help="Skip cover letter generation")

    # connect
    p_connect = sub.add_parser("connect", help="Send connection requests")
    p_connect.add_argument("--profile", help="Single profile URL")
    p_connect.add_argument("--profiles-file", help="File with profile URLs (one per line)")
    p_connect.add_argument("--note", help="Connection note")
    p_connect.add_argument("--no-note", action="store_true", help="Skip note")

    # post
    p_post = sub.add_parser("post", help="Create a LinkedIn post")
    p_post.add_argument("--text", help="Post text (or reads from stdin)")
    p_post.add_argument("--text-file", help="File containing post text")
    p_post.add_argument("--image", help="Path to image to attach")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "feed": cmd_feed,
        "comments": cmd_comments,
        "engage": cmd_engage,
        "apply": cmd_apply,
        "connect": cmd_connect,
        "post": cmd_post,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
