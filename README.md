# Ghost Browser — AI-Powered Browser Automation That Does Everything For You

> **The browser moves on its own. No human needed.**

Your browser opens. Types by itself. Scrolls LinkedIn. Posts content. Applies to jobs. Scrapes data from any website. Takes typing tests at 412 WPM. All while you watch.

**Built in one session with Claude Code + Playwright.**

![Demo Finale](assets/demo-finale.png)

---

## What This Can Do

| Capability | What Happens |
|---|---|
| **LinkedIn Auto-Post** | Opens LinkedIn, types your post, attaches image, clicks Post |
| **LinkedIn Engagement** | Scrolls feed, likes posts, writes AI-generated comments |
| **Job Applications** | Searches jobs, reads descriptions, applies with AI cover letters |
| **Universal Web Scraper** | Scrapes ANY website — Indeed, Google Maps, Hacker News, anything |
| **Ghost Typing** | Takes typing tests at 400+ WPM with 100% accuracy |
| **Speed Reading** | Opens Wikipedia, scrolls and highlights key information |
| **GitHub Trending** | Browses trending repos, opens top projects |
| **Stats Tracking** | Pulls followers/views from LinkedIn, Twitter, YouTube |
| **Screenshot Tool** | Screenshots any URL with custom viewports |

---

## The "WOW" Demo (Show This First)

```bash
python3 demo_wow.py
```

Watch the browser come alive:
1. **Google Search** — ghost types "How to build AI agents" letter by letter
2. **Wikipedia** — speed-reads AI article, highlights key paragraphs
3. **GitHub** — browses trending repos, clicks into the #1 project
4. **MonkeyType** — takes a typing test at ~400 WPM (world record is 300)
5. **Hacker News** — reads the top tech story
6. **Finale** — custom branded splash screen

No one is touching the keyboard. The browser does everything.

---

## Results

### MonkeyType — 412 WPM, 100% Accuracy

![MonkeyType Result](assets/monkeytype-412wpm.png)

> MonkeyType flagged it as "Test invalid" because no human can type this fast. The world record is ~300 WPM.

### LinkedIn — Auto-Posted with Image

![LinkedIn Auto-Post](assets/linkedin-autopost.png)

> Full post with image, typed and published automatically. "Post successful" confirmation at the bottom.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/aiwithdhruv/ghost-browser.git
cd ghost-browser

# 2. Install
pip install -r requirements.txt
playwright install chromium

# 3. Set up credentials
cp .env.example .env
# Add your LinkedIn li_at cookie (see below)

# 4. Run the demo
python3 demo_wow.py
```

**That's it. 4 commands. Watch the magic.**

---

## All Commands

### LinkedIn
```bash
# Post to LinkedIn with image
python3 linkedin_engage.py post --text "Your post here" --image photo.jpg --visible

# Post from a file
python3 linkedin_engage.py post --text-file post.txt --image banner.png --visible

# Scroll feed, see posts
python3 linkedin_engage.py feed --visible

# Check comments on your posts
python3 linkedin_engage.py comments --visible

# Auto-engage: like + AI comment on 5 posts
python3 linkedin_engage.py engage --count 5 --visible

# Search + apply to jobs
python3 linkedin_engage.py apply --query "AI engineer" --location "Remote" --visible

# Send connection requests
python3 linkedin_engage.py connect --profile "https://linkedin.com/in/someone" --note "Hey!" --visible
```

### Scrape Any Website
```bash
# Indeed jobs
python3 universal_scraper.py indeed --query "AI engineer" --output jobs.json

# Google Maps businesses
python3 universal_scraper.py google-maps --query "AI companies San Francisco" --output leads.json

# Any URL (smart mode auto-detects content)
python3 universal_scraper.py "https://news.ycombinator.com" --mode smart --output hn.json

# Custom CSS selector
python3 universal_scraper.py "https://example.com" --selector "h2.title" --output titles.json
```

### Stats & Screenshots
```bash
# Pull stats from all platforms
python3 stats_tracker.py --notify

# YouTube only (free API, no browser)
python3 stats_tracker.py --youtube-only

# Screenshot any URL
python3 screenshot_tool.py --url "https://example.com" --output screenshot.png

# LinkedIn profile screenshot
python3 screenshot_tool.py --preset linkedin --output linkedin.png
```

### Fun Demos
```bash
# The full WOW demo (6 stages)
python3 demo_wow.py

# MonkeyType speed demon (15 sec test, ~400 WPM)
python3 monkeytype_flex.py

# Job market research (LinkedIn + Indeed)
python3 job_research.py
```

---

## How It Works

### Architecture

```
human_behavior.py          ← Anti-detection: random delays, human typing, smooth scrolling
    ↓
base_browser.py            ← Playwright wrapper: cookie auth, navigation, screenshots
    ↓
├── linkedin_browser.py    ← LinkedIn: post, like, comment, apply, connect
├── linkedin_scraper.py    ← LinkedIn: followers, connections, post analytics
├── twitter_scraper.py     ← Twitter: followers, impressions
├── youtube_stats.py       ← YouTube API (no browser needed)
├── universal_scraper.py   ← Scrape ANY website with presets
└── screenshot_tool.py     ← Screenshot any URL
    ↓
├── linkedin_engage.py     ← CLI for all LinkedIn actions
├── stats_tracker.py       ← Master stats orchestrator
├── demo_wow.py            ← The viral demo
└── job_research.py        ← Job market research
```

### Human-Like Behavior (Anti-Detection)

The `human_behavior.py` engine makes every action look natural:

| Behavior | How |
|---|---|
| **Typing** | Character-by-character at 40-55 WPM with 3-5% typo rate (types wrong char, pauses, backspaces) |
| **Delays** | Gaussian distribution (not uniform) — clusters around midpoint like real humans |
| **Scrolling** | Sinusoidal speed curve — slow start, fast middle, slow end |
| **Clicking** | Random offset from element center (not dead-center like bots) |
| **Reading** | Calculates reading time based on word count, waits proportionally |
| **Breaks** | Takes 30-120 sec breaks every 15-25 actions |
| **Viewport** | Random realistic resolution from a pool (1440x900, 1920x1080, etc.) |

```python
# Ghost typing with typos
HumanBehavior.human_type(page, "input", "Hello world", wpm=45, typo_rate=0.05)

# Smooth scrolling (not instant jump)
HumanBehavior.human_scroll(page, "down", distance=600)

# Click with natural offset
HumanBehavior.human_click(page, "button.submit")

# Reading delay based on content length
HumanBehavior.reading_time("This is a long article about AI...")
```

### LinkedIn Post Flow

```
1. Open feed → Click "Start a post"
2. Find Quill editor (contenteditable div)
3. Short posts (<200 chars): type character-by-character with typos
   Long posts (>200 chars): insert_text (humans paste long posts too)
4. Click media button → upload image via file input
5. Click "Next" (LinkedIn's image editor step)
6. Click "Post" → confirmed!
```

### AI-Generated Comments

```python
# Uses GPT-4o-mini with your brand voice
BRAND_PROMPT = """You are Dhruv Tomar (AIwithDhruv), an Applied AI Engineer.
Your tone: 40% witty realism, 30% strategic clarity, 20% motivational.
Write SHORT comments (1-3 sentences). Be genuine, add value.
Never be generic ("Great post!"). Sound like a real person."""
```

---

## Getting Credentials

### LinkedIn `li_at` Cookie
1. Login to LinkedIn in Chrome
2. DevTools (F12) → Application → Cookies → `linkedin.com`
3. Copy `li_at` value → paste in `.env`

### YouTube API Key (FREE)
1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → Enable YouTube Data API v3
2. Create API Key → copy to `.env`
3. **Cost:** $0 (10,000 free units/day)

### Twitter Cookies
1. Login to x.com → DevTools → Application → Cookies
2. Copy `auth_token` and `ct0` → paste in `.env`

---

## Project Structure

```
ghost-browser/
├── README.md                 ← You are here
├── requirements.txt          ← pip dependencies
├── .env.example              ← Credential template
│
├── base_browser.py           ← Playwright base class (context manager)
├── human_behavior.py         ← Anti-detection engine
│
├── linkedin_browser.py       ← LinkedIn read + write operations
├── linkedin_engage.py        ← LinkedIn CLI (feed, post, engage, apply, connect)
├── linkedin_scraper.py       ← LinkedIn stats scraper
│
├── universal_scraper.py      ← Scrape any website (6 presets)
├── twitter_scraper.py        ← Twitter/X scraper
├── youtube_stats.py          ← YouTube API (no browser)
│
├── screenshot_tool.py        ← Universal screenshot tool
├── stats_tracker.py          ← Master stats + Telegram notifications
│
├── demo_wow.py               ← The viral demo (6 stages)
├── monkeytype_flex.py        ← Speed typing demo (400+ WPM)
├── job_research.py           ← Job market research (LinkedIn + Indeed)
│
├── assets/                   ← Screenshots for README
│   ├── monkeytype-412wpm.png
│   ├── linkedin-autopost.png
│   └── demo-finale.png
│
└── stats/                    ← Output data
    └── history.json
```

---

## Tech Stack

- **Playwright** — headless/visible Chrome automation
- **Python 3** — no heavy frameworks, just clean scripts
- **OpenAI API** — AI-generated comments and cover letters
- **YouTube Data API** — free stats without browser
- **dotenv** — credential management

---

## Use Cases (Make Money With This)

| Use Case | How | Revenue |
|---|---|---|
| **LinkedIn Automation Service** | Auto-post, engage, grow profiles for clients | $500-2000/mo per client |
| **Web Scraping Gigs** | Scrape leads, jobs, businesses on Fiverr/Upwork | $200-1000 per project |
| **LinkedIn Ghostwriting** | AI-write + auto-post for founders/CEOs | $500-1500/mo per client |
| **Job Application Bot** | Auto-apply to 100+ jobs for job seekers | $50-200 per person |
| **Lead Generation** | Scrape Google Maps → enrich → cold email | $500-2000/mo per client |
| **Stats Dashboard** | Track social metrics for influencers/brands | $100-500/mo per client |

---

## Built With

Built in one session using **Claude Code** (Anthropic's AI coding agent) + **Playwright**.

The entire toolkit — 15 files, 3000+ lines of code, LinkedIn automation, web scraping, human behavior simulation, typing demos — was designed, coded, tested, and deployed in a single sitting.

**No tutorials. No copy-paste. AI-generated architecture, human-verified execution.**

---

## Author

**Dhruv Tomar** — [@AIwithDhruv](https://linkedin.com/in/aiwithdhruv)

Applied AI Engineer & Solutions Architect | Building AI systems that actually ship.

---

## License

MIT — use it, modify it, sell services with it. Just don't blame me if LinkedIn sends you a stern email.

---

**Star this repo if the ghost browser blew your mind.**
