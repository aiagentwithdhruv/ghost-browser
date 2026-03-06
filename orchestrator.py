#!/usr/bin/env python3
"""
Ghost Browser Orchestrator — Run multiple browser agents in parallel.

Inspired by:
- Manus AI: Task decomposition → sandboxed execution → result aggregation
- OpenClaw: Heartbeat model (silent unless noteworthy) + skill-based routing
- Nick Saraev: 20 Chrome tabs doing 20 different things simultaneously

Usage:
    # Run pre-built agent combos
    python3 orchestrator.py --agents linkedin,scraper,demo --visible

    # LinkedIn engage + Indeed scrape simultaneously
    python3 orchestrator.py --agents linkedin,indeed --visible

    # Full demo — 3 agents at once for audience
    python3 orchestrator.py --demo --visible
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

from multi_context import MultiContextManager, BrowserSession
from human_behavior import HumanBehavior

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  AGENT TASKS — Each is a function that takes a BrowserSession
# ══════════════════════════════════════════════════════════════

def agent_linkedin_feed(session: BrowserSession):
    """Scroll LinkedIn feed and extract posts."""
    session.goto("https://www.linkedin.com/feed/", settle=3)
    HumanBehavior.warmup_delay()
    HumanBehavior.mouse_drift(session.page, steps=2)

    # Scroll through feed
    for i in range(4):
        session.scroll("down", random.randint(400, 700))
        HumanBehavior.random_delay(2.0, 4.0)
        if random.random() < 0.3:
            HumanBehavior.mouse_drift(session.page, steps=1)

    # Extract posts
    posts = session.evaluate("""
        (max) => {
            const results = [];
            const updates = document.querySelectorAll(
                '.feed-shared-update-v2, [data-urn*="urn:li:activity"]'
            );
            for (let i = 0; i < Math.min(updates.length, max); i++) {
                const post = updates[i];
                const authorEl = post.querySelector(
                    '.update-components-actor__name .visually-hidden, ' +
                    '.update-components-actor__title .visually-hidden'
                );
                const contentEl = post.querySelector(
                    '.feed-shared-text .break-words, ' +
                    '.update-components-text .break-words'
                );
                const author = authorEl ? authorEl.textContent.trim() : '';
                const content = contentEl ? contentEl.textContent.trim() : '';
                if (author || content) {
                    results.push({ author, content: content.substring(0, 300), index: i });
                }
            }
            return results;
        }
    """, 10)

    session._log(f"Found {len(posts)} posts")
    session.screenshot()
    return {"posts": posts, "count": len(posts)}


def agent_linkedin_engage(session: BrowserSession):
    """Like AI-related posts on LinkedIn feed with human behavior."""
    session.goto("https://www.linkedin.com/feed/", settle=3)
    HumanBehavior.warmup_delay()

    # Scroll to load posts
    for _ in range(3):
        session.scroll("down", random.randint(400, 700))
        HumanBehavior.random_delay(2.0, 4.0)

    # Find and like posts via JS
    liked = session.evaluate("""
        () => {
            const posts = document.querySelectorAll(
                '.feed-shared-update-v2, [data-urn*="urn:li:activity"]'
            );
            let liked = 0;
            for (let i = 0; i < Math.min(posts.length, 5); i++) {
                const post = posts[i];
                const btn = post.querySelector(
                    'button[aria-label*="Like"]:not([aria-pressed="true"]), ' +
                    'button[aria-label*="like"]:not([aria-pressed="true"])'
                );
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.y > 0 && rect.y < window.innerHeight) {
                        post.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        liked++;
                    }
                }
            }
            return { total_posts: posts.length, likeable: liked };
        }
    """)

    # Like posts one by one with human timing
    posts = session.evaluate("""
        () => {
            const posts = document.querySelectorAll(
                '.feed-shared-update-v2, [data-urn*="urn:li:activity"]'
            );
            const results = [];
            for (let i = 0; i < Math.min(posts.length, 5); i++) {
                const post = posts[i];
                const btn = post.querySelector(
                    'button[aria-label*="Like"]:not([aria-pressed="true"])'
                );
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    results.push({ index: i, x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
                }
            }
            return results;
        }
    """)

    liked_count = 0
    for post in posts[:3]:  # Like up to 3
        try:
            # Scroll to post
            session.evaluate(f"""
                () => {{
                    const posts = document.querySelectorAll(
                        '.feed-shared-update-v2, [data-urn*="urn:li:activity"]'
                    );
                    if (posts[{post['index']}]) {{
                        posts[{post['index']}].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                }}
            """)
            HumanBehavior.random_delay(2.0, 5.0)  # Read the post

            # Click like with human offset
            x = post["x"] + random.uniform(-3, 3)
            y = post["y"] + random.uniform(-3, 3)
            HumanBehavior.random_delay(0.3, 0.8)
            session.page.mouse.click(x, y)
            liked_count += 1
            session._log(f"Liked post #{post['index']}")

            # Between-post delay
            HumanBehavior.random_delay(5.0, 12.0)
        except Exception as e:
            session._log(f"Like failed: {e}")

    session.screenshot()
    return {"liked": liked_count, "available": len(posts)}


def agent_scrape_indeed(session: BrowserSession, query="AI engineer"):
    """Scrape Indeed job listings."""
    url = f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l=Remote"
    session.goto(url, settle=3)
    HumanBehavior.warmup_delay()

    for _ in range(3):
        session.scroll("down", random.randint(300, 600))
        HumanBehavior.random_delay(1.5, 3.0)

    jobs = session.evaluate("""
        () => {
            const results = [];
            const cards = document.querySelectorAll(
                '.job_seen_beacon, .jobsearch-ResultsList .result, [data-jk]'
            );
            for (let i = 0; i < Math.min(cards.length, 15); i++) {
                const card = cards[i];
                const titleEl = card.querySelector('h2 a, .jobTitle a, [data-jk] a');
                const companyEl = card.querySelector('[data-testid="company-name"], .companyName');
                const locationEl = card.querySelector('[data-testid="text-location"], .companyLocation');
                results.push({
                    title: titleEl ? titleEl.textContent.trim() : '',
                    company: companyEl ? companyEl.textContent.trim() : '',
                    location: locationEl ? locationEl.textContent.trim() : '',
                    url: titleEl ? titleEl.href : '',
                });
            }
            return results;
        }
    """)

    session._log(f"Scraped {len(jobs)} jobs for '{query}'")
    session.screenshot()
    return {"jobs": jobs, "query": query, "count": len(jobs)}


def agent_scrape_gmaps(session: BrowserSession, query="AI companies"):
    """Scrape Google Maps business listings."""
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    session.goto(url, settle=4)
    HumanBehavior.warmup_delay()

    # Scroll the results panel
    for _ in range(5):
        session.evaluate("""
            () => {
                const panel = document.querySelector('[role="feed"]') ||
                              document.querySelector('.m6QErb');
                if (panel) panel.scrollBy(0, 400);
            }
        """)
        HumanBehavior.random_delay(1.5, 3.0)

    businesses = session.evaluate("""
        () => {
            const results = [];
            const items = document.querySelectorAll('[role="feed"] > div > div > a, .Nv2PK a.hfpxzc');
            for (let i = 0; i < Math.min(items.length, 20); i++) {
                const item = items[i];
                const name = item.getAttribute('aria-label') || item.textContent.trim();
                const url = item.href || '';
                results.push({ name, url, index: i });
            }
            return results;
        }
    """)

    session._log(f"Found {len(businesses)} businesses for '{query}'")
    session.screenshot()
    return {"businesses": businesses, "query": query, "count": len(businesses)}


def agent_monkeytype(session: BrowserSession):
    """Run MonkeyType speed typing demo."""
    session.goto("https://monkeytype.com", settle=3)
    HumanBehavior.warmup_delay()

    # Dismiss cookie banner
    try:
        session.page.locator('button.rejectAll, .cookieBar .acceptAll, button:has-text("Accept")').first.click(timeout=3000)
        HumanBehavior.random_delay(0.5, 1.0)
    except Exception:
        pass

    # Set 15-second mode
    try:
        session.page.locator('button[data-mode="time"]').first.click(timeout=3000)
        HumanBehavior.micro_delay()
        session.page.locator('button[data-time="15"]').first.click(timeout=3000)
        session._log("15 second mode set")
        HumanBehavior.random_delay(0.5, 1.0)
    except Exception:
        session._log("Could not set 15s mode, using default")

    # Get words and type them superfast
    words = session.evaluate("""
        () => {
            const els = document.querySelectorAll('.word');
            return Array.from(els).map(w => w.textContent).join(' ');
        }
    """)

    if not words:
        session._log("No words found")
        return {"error": "no words found"}

    session._log("GO GO GO!")
    start = time.time()

    for char in words:
        session.page.keyboard.type(char, delay=0)
        time.sleep(random.uniform(0.010, 0.025))

        if time.time() - start > 16:
            break

    elapsed = time.time() - start
    chars = len(words[:int(elapsed * 30)])
    wpm = int((chars / 5) / (elapsed / 60)) if elapsed > 0 else 0

    session._log(f"Speed: ~{wpm} WPM in {elapsed:.1f}s")

    HumanBehavior.random_delay(2, 4)  # Wait for results
    path = session.screenshot()

    return {"wpm": wpm, "elapsed": elapsed, "screenshot": path}


def agent_github_trending(session: BrowserSession):
    """Browse GitHub trending repos."""
    session.goto("https://github.com/trending", settle=3)
    HumanBehavior.warmup_delay()

    for _ in range(3):
        session.scroll("down", random.randint(300, 600))
        HumanBehavior.random_delay(1.5, 3.0)

    repos = session.evaluate("""
        () => {
            const results = [];
            const rows = document.querySelectorAll('article.Box-row, .Box-row');
            for (let i = 0; i < Math.min(rows.length, 10); i++) {
                const row = rows[i];
                const nameEl = row.querySelector('h2 a, h1 a');
                const descEl = row.querySelector('p');
                const starsEl = row.querySelector('[href*="/stargazers"], .f6 a');
                results.push({
                    name: nameEl ? nameEl.textContent.trim().replace(/\\s+/g, '') : '',
                    description: descEl ? descEl.textContent.trim() : '',
                    stars: starsEl ? starsEl.textContent.trim() : '',
                    url: nameEl ? 'https://github.com' + nameEl.getAttribute('href') : '',
                });
            }
            return results;
        }
    """)

    session._log(f"Found {len(repos)} trending repos")
    session.screenshot()
    return {"repos": repos, "count": len(repos)}


def agent_twitter_trending(session: BrowserSession, query="AI agents"):
    """Scrape Twitter/X trending topics and top posts.

    Requires TWITTER_AUTH_TOKEN + TWITTER_CT0 cookies in .env.
    Get them: x.com → DevTools → Application → Cookies → copy auth_token & ct0.
    """
    auth_token = os.getenv("TWITTER_AUTH_TOKEN")
    ct0 = os.getenv("TWITTER_CT0")

    if not auth_token or not ct0:
        session._log("No Twitter cookies set — set TWITTER_AUTH_TOKEN + TWITTER_CT0 in .env")
        return {
            "error": "Twitter requires auth cookies. Add TWITTER_AUTH_TOKEN and TWITTER_CT0 to .env",
            "setup": "x.com → DevTools (F12) → Application → Cookies → copy auth_token & ct0",
            "trends": [], "tweets": [], "trend_count": 0, "tweet_count": 0,
        }

    # Inject cookies
    session.context.add_cookies([
        {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
        {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
    ])

    # Go to trending or search
    if query:
        session.goto(f"https://x.com/search?q={query.replace(' ', '+')}&src=typed_query&f=top", settle=4)
    else:
        session.goto("https://x.com/explore/tabs/trending", settle=4)

    HumanBehavior.warmup_delay()

    for _ in range(3):
        session.scroll("down", random.randint(300, 600))
        HumanBehavior.random_delay(1.5, 3.0)

    # Extract trending topics
    trends = session.evaluate("""
        () => {
            const results = [];
            const cells = document.querySelectorAll(
                '[data-testid="trend"], [data-testid="cellInnerDiv"]'
            );
            for (let i = 0; i < Math.min(cells.length, 20); i++) {
                const cell = cells[i];
                const spans = cell.querySelectorAll('span');
                const texts = Array.from(spans)
                    .map(s => s.textContent.trim())
                    .filter(t => t && t.length > 2 && !t.startsWith('·'));
                if (texts.length >= 1) {
                    const trendName = texts.find(t =>
                        t.startsWith('#') || (t.length > 3 && !t.match(/^\\d+/))
                    ) || texts[0];
                    const postCount = texts.find(t =>
                        t.match(/posts|tweets|K |M /i)
                    ) || '';
                    const category = texts.find(t =>
                        t.match(/trending|politics|sports|tech|entertainment|business/i)
                    ) || '';
                    if (trendName && !results.some(r => r.topic === trendName)) {
                        results.push({ topic: trendName, posts: postCount, category });
                    }
                }
            }
            return results;
        }
    """)

    # Extract tweets
    tweets = session.evaluate("""
        () => {
            const results = [];
            const tweetEls = document.querySelectorAll(
                '[data-testid="tweet"], article[role="article"]'
            );
            for (let i = 0; i < Math.min(tweetEls.length, 10); i++) {
                const tweet = tweetEls[i];
                const userEl = tweet.querySelector('[data-testid="User-Name"]');
                const textEl = tweet.querySelector('[data-testid="tweetText"]');
                if (textEl) {
                    results.push({
                        user: userEl ? userEl.textContent.trim().split('·')[0].trim() : '',
                        text: textEl.textContent.trim().substring(0, 280),
                    });
                }
            }
            return results;
        }
    """)

    session._log(f"Found {len(trends)} trends, {len(tweets)} tweets")
    session.screenshot()
    return {"trends": trends[:15], "tweets": tweets[:10],
            "query": query, "trend_count": len(trends), "tweet_count": len(tweets)}


def agent_hacker_news(session: BrowserSession):
    """Read top Hacker News stories."""
    session.goto("https://news.ycombinator.com", settle=2)
    HumanBehavior.warmup_delay()

    session.scroll("down", 400)
    HumanBehavior.random_delay(1, 3)

    stories = session.evaluate("""
        () => {
            const results = [];
            const rows = document.querySelectorAll('.athing');
            for (let i = 0; i < Math.min(rows.length, 10); i++) {
                const row = rows[i];
                const link = row.querySelector('.titleline a');
                const subtext = row.nextElementSibling;
                const score = subtext ? subtext.querySelector('.score') : null;
                results.push({
                    title: link ? link.textContent : '',
                    url: link ? link.href : '',
                    points: score ? score.textContent : '0',
                });
            }
            return results;
        }
    """)

    session._log(f"Found {len(stories)} stories")
    session.screenshot()
    return {"stories": stories, "count": len(stories)}


# ══════════════════════════════════════════════════════════════
#  AGENT REGISTRY — Maps names to (setup_fn, task_fn) pairs
# ══════════════════════════════════════════════════════════════

AGENTS = {
    "linkedin-feed": {
        "description": "Scroll LinkedIn feed, extract posts",
        "setup": lambda m: m.create_linkedin_session(),
        "task": agent_linkedin_feed,
        "session_name": "linkedin",
    },
    "linkedin-engage": {
        "description": "Like AI-related posts on LinkedIn",
        "setup": lambda m: m.create_linkedin_session(),
        "task": agent_linkedin_engage,
        "session_name": "linkedin",
    },
    "indeed": {
        "description": "Scrape Indeed job listings",
        "setup": lambda m: m.create_scraper_session("indeed"),
        "task": lambda s: agent_scrape_indeed(s, "AI engineer"),
        "session_name": "indeed",
    },
    "gmaps": {
        "description": "Scrape Google Maps businesses",
        "setup": lambda m: m.create_scraper_session("gmaps"),
        "task": lambda s: agent_scrape_gmaps(s, "AI companies"),
        "session_name": "gmaps",
    },
    "monkeytype": {
        "description": "Speed typing demo (~400 WPM)",
        "setup": lambda m: m.create_demo_session("monkeytype"),
        "task": agent_monkeytype,
        "session_name": "monkeytype",
    },
    "github": {
        "description": "Browse GitHub trending repos",
        "setup": lambda m: m.create_scraper_session("github"),
        "task": agent_github_trending,
        "session_name": "github",
    },
    "hackernews": {
        "description": "Read top Hacker News stories",
        "setup": lambda m: m.create_scraper_session("hackernews"),
        "task": agent_hacker_news,
        "session_name": "hackernews",
    },
    "twitter": {
        "description": "Scrape Twitter/X trending topics & tweets",
        "setup": lambda m: m.create_scraper_session("twitter"),
        "task": agent_twitter_trending,
        "session_name": "twitter",
    },
}

# Pre-built combos
COMBOS = {
    "demo": ["monkeytype", "github", "hackernews"],
    "research": ["linkedin-feed", "indeed", "github", "twitter"],
    "lead-gen": ["linkedin-feed", "gmaps", "indeed"],
    "social": ["linkedin-feed", "twitter", "hackernews"],
    "full": ["linkedin-engage", "indeed", "gmaps", "github", "hackernews", "twitter"],
}


# ══════════════════════════════════════════════════════════════
#  ORCHESTRATOR — Main entry point
# ══════════════════════════════════════════════════════════════

def run_orchestrator(agent_names, headless=False, save_results=True):
    """
    Run multiple agents in parallel.

    Args:
        agent_names: List of agent names from AGENTS registry
        headless: Run browser without GUI
        save_results: Save results to JSON

    Returns:
        Dict of {agent_name: result}
    """
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  GHOST BROWSER ORCHESTRATOR", file=sys.stderr)
    print(f"  Agents: {', '.join(agent_names)}", file=sys.stderr)
    print(f"  Mode: {'headless' if headless else 'visible'}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    manager = MultiContextManager(headless=headless)
    manager.start()

    try:
        # Create sessions for each agent
        tasks = []
        for name in agent_names:
            if name not in AGENTS:
                print(f"  Unknown agent: {name}. Available: {list(AGENTS.keys())}", file=sys.stderr)
                continue

            agent = AGENTS[name]
            try:
                agent["setup"](manager)
                tasks.append((agent["session_name"], agent["task"]))
                print(f"  [{name}] Ready", file=sys.stderr)
            except Exception as e:
                print(f"  [{name}] Setup failed: {e}", file=sys.stderr)

        if not tasks:
            print("No agents ready. Exiting.", file=sys.stderr)
            return {}

        # Run all agents in parallel
        print(f"\nLaunching {len(tasks)} agents in parallel...\n", file=sys.stderr)
        start = time.time()
        results = manager.run_parallel(tasks)
        elapsed = time.time() - start

        # Summary
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  RESULTS (completed in {elapsed:.1f}s)", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        for name, result in results.items():
            if "error" in result:
                print(f"  [{name}] ERROR: {result['error']}", file=sys.stderr)
            else:
                r = result.get("result", {})
                # Summarize based on type
                if "posts" in r:
                    print(f"  [{name}] {r['count']} posts extracted", file=sys.stderr)
                elif "jobs" in r:
                    print(f"  [{name}] {r['count']} jobs scraped", file=sys.stderr)
                elif "businesses" in r:
                    print(f"  [{name}] {r['count']} businesses found", file=sys.stderr)
                elif "wpm" in r:
                    print(f"  [{name}] {r['wpm']} WPM typing speed", file=sys.stderr)
                elif "repos" in r:
                    print(f"  [{name}] {r['count']} trending repos", file=sys.stderr)
                elif "stories" in r:
                    print(f"  [{name}] {r['count']} stories", file=sys.stderr)
                elif "liked" in r:
                    print(f"  [{name}] {r['liked']} posts liked", file=sys.stderr)
                elif "trends" in r:
                    print(f"  [{name}] {r['trend_count']} trends, {r['tweet_count']} tweets", file=sys.stderr)
                else:
                    print(f"  [{name}] Done", file=sys.stderr)

        # Save results
        if save_results:
            out_file = os.path.join(
                RESULTS_DIR,
                f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(out_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "agents": agent_names,
                    "elapsed_seconds": elapsed,
                    "results": results,
                }, f, indent=2, default=str)
            print(f"\n  Results saved: {out_file}", file=sys.stderr)

        # Screenshots
        shots = manager.screenshot_all()
        print(f"  Screenshots: {list(shots.values())}", file=sys.stderr)

        # Keep browser open for viewing
        print(f"\n  Browser stays open 15s for viewing...", file=sys.stderr)
        time.sleep(15)

        return results

    finally:
        manager.stop()


# ══════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Ghost Browser Orchestrator — run multiple browser agents in parallel"
    )
    parser.add_argument(
        "--agents", type=str,
        help=f"Comma-separated agent names: {', '.join(AGENTS.keys())}"
    )
    parser.add_argument(
        "--combo", type=str, choices=list(COMBOS.keys()),
        help=f"Pre-built agent combo: {', '.join(COMBOS.keys())}"
    )
    parser.add_argument("--demo", action="store_true", help="Run demo combo (MonkeyType + GitHub + HN)")
    parser.add_argument("--visible", action="store_true", help="Show browser windows")
    parser.add_argument("--list", action="store_true", help="List available agents and combos")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Agents:")
        for name, info in AGENTS.items():
            print(f"  {name:20s} — {info['description']}")
        print("\nPre-built Combos:")
        for name, agents in COMBOS.items():
            print(f"  {name:20s} — {', '.join(agents)}")
        return

    # Determine which agents to run
    if args.demo:
        agent_names = COMBOS["demo"]
    elif args.combo:
        agent_names = COMBOS[args.combo]
    elif args.agents:
        agent_names = [a.strip() for a in args.agents.split(",")]
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python3 orchestrator.py --demo --visible")
        print("  python3 orchestrator.py --agents linkedin-feed,indeed,github --visible")
        print("  python3 orchestrator.py --combo lead-gen --visible")
        return

    run_orchestrator(agent_names, headless=not args.visible)


if __name__ == "__main__":
    main()
