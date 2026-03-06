#!/usr/bin/env python3
"""
Ghost Browser MCP Server — Expose browser automation tools via Model Context Protocol.

Any AI agent (Claude Code, Cursor, Codex, etc.) can control Ghost Browser through MCP.

Setup in Claude Desktop / claude_desktop_config.json:
    {
        "mcpServers": {
            "ghost-browser": {
                "command": "python3",
                "args": ["/path/to/ghost_mcp.py"],
                "env": {
                    "LINKEDIN_LI_AT": "your_cookie_here",
                    "OPENAI_API_KEY": "sk-..."
                }
            }
        }
    }

Tools exposed:
    - linkedin_feed: Get LinkedIn feed posts
    - linkedin_post: Create a LinkedIn post
    - linkedin_engage: Like posts on LinkedIn
    - scrape_url: Scrape any website
    - scrape_indeed: Scrape Indeed jobs
    - scrape_gmaps: Scrape Google Maps businesses
    - scrape_twitter: Scrape Twitter/X trends and tweets
    - typing_demo: Run MonkeyType speed test
    - screenshot: Take screenshot of any URL
    - multi_run: Run multiple agents in parallel
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Install MCP: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

# Initialize MCP server
mcp = FastMCP(
    "Ghost Browser",
    description="AI-powered browser automation with human-like behavior. "
                "LinkedIn engagement, web scraping, speed typing demos, "
                "and multi-agent parallel execution.",
)


# ── LinkedIn Tools ─────────────────────────────────────────

@mcp.tool()
def linkedin_feed(count: int = 5) -> str:
    """
    Get LinkedIn feed posts. Returns post authors and content.

    Args:
        count: Number of posts to fetch (default 5, max 20)
    """
    from linkedin_browser import LinkedInBrowser

    browser = LinkedInBrowser(headless=True)
    browser.start()
    try:
        posts = browser.get_feed_posts(count=min(count, 20))
        result = []
        for p in posts:
            result.append({
                "author": p.get("author", ""),
                "headline": p.get("headline", ""),
                "content": p.get("content", "")[:300],
                "url": p.get("post_url", ""),
                "liked": p.get("is_liked", False),
            })
        return json.dumps(result, indent=2)
    finally:
        browser.stop()


@mcp.tool()
def linkedin_post(text: str, image_path: str = "") -> str:
    """
    Create a LinkedIn post with optional image. Types text with human-like behavior.

    Args:
        text: Post content (supports newlines)
        image_path: Optional path to image file to attach
    """
    from linkedin_browser import LinkedInBrowser

    browser = LinkedInBrowser(headless=False)
    browser.start()
    try:
        success = browser.create_post(text, image_path=image_path if image_path else None)
        return json.dumps({"success": success, "content_preview": text[:100]})
    finally:
        browser.stop()


@mcp.tool()
def linkedin_engage(count: int = 3, like_only: bool = True) -> str:
    """
    Engage with LinkedIn feed posts — like and optionally comment.
    Uses human-like behavior (reading delays, random skips, mouse drift).

    Args:
        count: Number of posts to engage with (default 3)
        like_only: Only like posts, skip commenting (default True)
    """
    from linkedin_browser import LinkedInBrowser
    from human_behavior import HumanBehavior
    import random

    browser = LinkedInBrowser(headless=True)
    browser.start()
    try:
        posts = browser.get_feed_posts(count=count * 3)
        engaged = 0
        results = []

        for post in posts:
            if engaged >= count:
                break
            if post.get("is_liked"):
                continue

            # Like with human behavior
            success = browser.like_post(post_index=post["index"])
            if success:
                engaged += 1
                results.append({
                    "author": post.get("author", ""),
                    "action": "liked",
                    "content_preview": post.get("content", "")[:100],
                })
            HumanBehavior.random_delay(5.0, 12.0)

        return json.dumps({"engaged": engaged, "posts": results})
    finally:
        browser.stop()


# ── Scraping Tools ─────────────────────────────────────────

@mcp.tool()
def scrape_url(url: str, selector: str = "") -> str:
    """
    Scrape any website. Returns page title, text content, and links.
    Optionally extract specific elements with a CSS selector.

    Args:
        url: URL to scrape
        selector: Optional CSS selector to extract specific elements
    """
    from multi_context import MultiContextManager
    from human_behavior import HumanBehavior

    manager = MultiContextManager(headless=True)
    manager.start()
    try:
        session = manager.create_session("scraper")
        session.goto(url, settle=2)
        HumanBehavior.warmup_delay()

        if selector:
            data = session.evaluate(f"""
                () => {{
                    const els = document.querySelectorAll('{selector}');
                    return Array.from(els).map(el => el.textContent.trim()).filter(t => t);
                }}
            """)
            return json.dumps({"url": url, "selector": selector, "results": data[:50]})
        else:
            data = session.evaluate("""
                () => ({
                    title: document.title,
                    text: document.body.innerText.substring(0, 3000),
                    links: Array.from(document.querySelectorAll('a[href]'))
                        .slice(0, 20)
                        .map(a => ({ text: a.textContent.trim(), href: a.href }))
                        .filter(l => l.text && l.href.startsWith('http')),
                })
            """)
            return json.dumps({"url": url, **data})
    finally:
        manager.stop()


@mcp.tool()
def scrape_indeed(query: str = "AI engineer", location: str = "Remote") -> str:
    """
    Scrape Indeed job listings. Returns job titles, companies, and locations.

    Args:
        query: Job search query (default "AI engineer")
        location: Job location (default "Remote")
    """
    from orchestrator import agent_scrape_indeed
    from multi_context import MultiContextManager

    manager = MultiContextManager(headless=True)
    manager.start()
    try:
        session = manager.create_scraper_session("indeed")
        result = agent_scrape_indeed(session, query)
        return json.dumps(result)
    finally:
        manager.stop()


@mcp.tool()
def scrape_gmaps(query: str = "AI companies") -> str:
    """
    Scrape Google Maps business listings. Returns business names and URLs.

    Args:
        query: Search query for Google Maps (default "AI companies")
    """
    from orchestrator import agent_scrape_gmaps
    from multi_context import MultiContextManager

    manager = MultiContextManager(headless=True)
    manager.start()
    try:
        session = manager.create_scraper_session("gmaps")
        result = agent_scrape_gmaps(session, query)
        return json.dumps(result)
    finally:
        manager.stop()


@mcp.tool()
def scrape_twitter(topic: str = "AI agents") -> str:
    """
    Scrape Twitter/X trending topics and tweets.
    Uses cookie auth if TWITTER_AUTH_TOKEN is set, otherwise falls back to Nitter.

    Args:
        topic: Topic to search for (default "AI agents")
    """
    from orchestrator import agent_twitter_trending
    from multi_context import MultiContextManager

    manager = MultiContextManager(headless=True)
    manager.start()
    try:
        session = manager.create_scraper_session("twitter")
        result = agent_twitter_trending(session, query=topic)
        return json.dumps(result, indent=2)
    finally:
        manager.stop()


# ── Demo Tools ─────────────────────────────────────────────

@mcp.tool()
def typing_demo() -> str:
    """
    Run MonkeyType speed typing demo. Opens MonkeyType and types at ~400 WPM.
    Returns WPM score and screenshot path.
    """
    from orchestrator import agent_monkeytype
    from multi_context import MultiContextManager

    manager = MultiContextManager(headless=False)
    manager.start()
    try:
        session = manager.create_demo_session("monkeytype")
        result = agent_monkeytype(session)
        return json.dumps(result)
    finally:
        manager.stop()


@mcp.tool()
def screenshot(url: str) -> str:
    """
    Take a screenshot of any URL. Returns the screenshot file path.

    Args:
        url: URL to screenshot
    """
    from multi_context import MultiContextManager

    manager = MultiContextManager(headless=True)
    manager.start()
    try:
        session = manager.create_session("screenshot")
        session.goto(url, settle=3)
        path = session.screenshot()
        return json.dumps({"url": url, "screenshot": path})
    finally:
        manager.stop()


# ── Multi-Agent Tools ──────────────────────────────────────

@mcp.tool()
def multi_run(agents: str = "github,hackernews") -> str:
    """
    Run multiple browser agents simultaneously in parallel.
    Each agent gets its own isolated browser session.

    Available agents: linkedin-feed, linkedin-engage, indeed, gmaps,
                      monkeytype, github, hackernews

    Pre-built combos: demo, research, lead-gen, full

    Args:
        agents: Comma-separated agent names or combo name
                (e.g., "github,hackernews" or "demo" or "lead-gen")
    """
    from orchestrator import run_orchestrator, COMBOS, AGENTS

    # Check if it's a combo name
    if agents in COMBOS:
        agent_list = COMBOS[agents]
    else:
        agent_list = [a.strip() for a in agents.split(",")]

    # Validate
    valid = [a for a in agent_list if a in AGENTS]
    if not valid:
        return json.dumps({
            "error": f"No valid agents. Available: {list(AGENTS.keys())}",
            "combos": COMBOS,
        })

    results = run_orchestrator(valid, headless=True, save_results=True)
    return json.dumps(results, default=str)


# ── Resources ──────────────────────────────────────────────

@mcp.resource("ghost-browser://agents")
def list_agents() -> str:
    """List all available browser agents and combos."""
    from orchestrator import AGENTS, COMBOS
    return json.dumps({
        "agents": {k: v["description"] for k, v in AGENTS.items()},
        "combos": COMBOS,
    }, indent=2)


# ── Run ────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
