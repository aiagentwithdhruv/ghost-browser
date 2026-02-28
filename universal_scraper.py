#!/usr/bin/env python3
"""
Universal Web Scraper — works on ANY website with smart content extraction.
Uses Playwright (real browser) so it handles JavaScript-rendered pages.

Built-in presets for popular directories:
  Google Maps, Yellow Pages, JustDial, IndiaMART, Yelp, Craigslist, Indeed, Glassdoor

Usage:
    # Scrape any URL
    python3 universal_scraper.py https://example.com

    # Use presets
    python3 universal_scraper.py google-maps --query "plumbers in Austin TX"
    python3 universal_scraper.py yellowpages --query "dentists" --location "New York"
    python3 universal_scraper.py justdial --query "restaurants in Mumbai"
    python3 universal_scraper.py indeed --query "AI engineer" --location "Remote"

    # Extract specific elements
    python3 universal_scraper.py https://example.com --selector ".product-card" --fields "name,price,link"

    # Full page content dump
    python3 universal_scraper.py https://example.com --mode full --output data.json

    # Multi-page pagination
    python3 universal_scraper.py yellowpages --query "plumbers" --location "Texas" --pages 5
"""

import os
import sys
import json
import time
import random
import argparse
import csv
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin

sys.path.insert(0, os.path.dirname(__file__))
from base_browser import BaseBrowser
from human_behavior import HumanBehavior

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

STATS_DIR = os.path.join(os.path.dirname(__file__), "stats")
os.makedirs(STATS_DIR, exist_ok=True)


class UniversalScraper:
    """
    Scrape any website using Playwright with smart content extraction.
    Works on JS-rendered pages. Human-like behavior for stealth.
    """

    def __init__(self, headless=True, cookies=None):
        self.headless = headless
        self.cookies = cookies or []
        self.browser = None

    def _make_browser(self):
        vp = HumanBehavior.random_viewport()
        return BaseBrowser(
            cookies=self.cookies, headless=self.headless, viewport=vp
        )

    # ── Generic Extraction ──────────────────────────────────

    def scrape_url(self, url, mode="smart", selector=None, fields=None, scroll_pages=1):
        """
        Scrape a single URL and extract structured content.

        Args:
            url: URL to scrape
            mode: "smart" (auto-detect), "full" (everything), "selector" (CSS target)
            selector: CSS selector to target specific elements
            fields: Comma-separated field names for selector mode
            scroll_pages: How many times to scroll for infinite-scroll pages

        Returns:
            dict with extracted content
        """
        with self._make_browser() as b:
            b.goto(url, settle=3)

            # Scroll to load dynamic content
            for _ in range(scroll_pages):
                HumanBehavior.human_scroll(b.page, "down", random.randint(500, 900))
                HumanBehavior.random_delay(1, 2)

            if mode == "selector" and selector:
                return self._extract_by_selector(b, selector, fields)
            elif mode == "full":
                return self._extract_full(b, url)
            else:
                return self._extract_smart(b, url)

    def _extract_smart(self, browser, url):
        """Auto-detect content type and extract intelligently."""
        return browser.evaluate("""
            () => {
                const result = {
                    url: window.location.href,
                    title: document.title,
                    meta_description: '',
                    headings: [],
                    paragraphs: [],
                    links: [],
                    images: [],
                    tables: [],
                    lists: [],
                    contacts: { emails: [], phones: [], addresses: [] },
                    structured_data: [],
                };

                // Meta description
                const meta = document.querySelector('meta[name="description"]');
                if (meta) result.meta_description = meta.content;

                // Headings
                document.querySelectorAll('h1, h2, h3').forEach(h => {
                    const text = h.textContent.trim();
                    if (text) result.headings.push({ level: h.tagName, text: text.substring(0, 200) });
                });

                // Paragraphs (meaningful ones only)
                document.querySelectorAll('p').forEach(p => {
                    const text = p.textContent.trim();
                    if (text.length > 20) result.paragraphs.push(text.substring(0, 500));
                });
                result.paragraphs = result.paragraphs.slice(0, 30);

                // Links with text
                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.textContent.trim();
                    const href = a.href;
                    if (text && href && !href.startsWith('javascript:') && text.length > 2) {
                        result.links.push({ text: text.substring(0, 100), href });
                    }
                });
                result.links = result.links.slice(0, 50);

                // Images
                document.querySelectorAll('img[src]').forEach(img => {
                    const alt = img.alt || '';
                    const src = img.src;
                    if (src && !src.includes('data:image')) {
                        result.images.push({ alt, src });
                    }
                });
                result.images = result.images.slice(0, 20);

                // Tables
                document.querySelectorAll('table').forEach(table => {
                    const rows = [];
                    table.querySelectorAll('tr').forEach(tr => {
                        const cells = [];
                        tr.querySelectorAll('td, th').forEach(cell => {
                            cells.push(cell.textContent.trim());
                        });
                        if (cells.length > 0) rows.push(cells);
                    });
                    if (rows.length > 0) result.tables.push(rows.slice(0, 50));
                });

                // Lists
                document.querySelectorAll('ul, ol').forEach(list => {
                    const items = [];
                    list.querySelectorAll('li').forEach(li => {
                        const text = li.textContent.trim();
                        if (text.length > 5) items.push(text.substring(0, 200));
                    });
                    if (items.length > 1) result.lists.push(items.slice(0, 20));
                });
                result.lists = result.lists.slice(0, 10);

                // Extract contacts from page text
                const pageText = document.body.innerText || '';
                const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                const phoneRegex = /(?:\\+?\\d{1,3}[-.\\s]?)?\\(?\\d{2,4}\\)?[-.\\s]?\\d{3,4}[-.\\s]?\\d{3,4}/g;
                result.contacts.emails = [...new Set(pageText.match(emailRegex) || [])].slice(0, 10);
                result.contacts.phones = [...new Set(pageText.match(phoneRegex) || [])]
                    .filter(p => p.replace(/\\D/g, '').length >= 7)
                    .slice(0, 10);

                // JSON-LD structured data
                document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                    try {
                        result.structured_data.push(JSON.parse(s.textContent));
                    } catch(e) {}
                });

                return result;
            }
        """)

    def _extract_full(self, browser, url):
        """Extract everything from the page."""
        smart = self._extract_smart(browser, url)
        smart["full_text"] = browser.evaluate(
            "() => document.body.innerText.substring(0, 50000)"
        )
        smart["html_length"] = browser.evaluate(
            "() => document.documentElement.outerHTML.length"
        )
        return smart

    def _extract_by_selector(self, browser, selector, fields_str=None):
        """Extract elements matching a CSS selector with optional field mapping."""
        fields = [f.strip() for f in fields_str.split(",")] if fields_str else None

        return browser.evaluate("""
            (args) => {
                const [selector, fields] = args;
                const elements = document.querySelectorAll(selector);
                const results = [];

                elements.forEach(el => {
                    if (fields && fields.length > 0) {
                        const item = {};
                        fields.forEach(field => {
                            // Try common patterns for each field
                            const selectors = [
                                `[class*="${field}" i]`, `[data-${field}]`,
                                `.${field}`, `#${field}`,
                                `[itemprop="${field}"]`,
                            ];
                            for (const sel of selectors) {
                                const found = el.querySelector(sel);
                                if (found) {
                                    item[field] = found.textContent.trim();
                                    break;
                                }
                            }
                            if (!item[field]) {
                                // Fallback: search text content for field-like patterns
                                item[field] = null;
                            }
                        });
                        // Always include the full text as fallback
                        item['_text'] = el.textContent.trim().substring(0, 500);
                        item['_href'] = el.querySelector('a')?.href || '';
                        results.push(item);
                    } else {
                        results.push({
                            text: el.textContent.trim().substring(0, 500),
                            href: el.querySelector('a')?.href || '',
                            html: el.innerHTML.substring(0, 1000),
                        });
                    }
                });
                return results;
            }
        """, [selector, fields])

    # ── Pagination ──────────────────────────────────────────

    def scrape_paginated(self, url_template, pages=5, mode="smart", selector=None,
                         fields=None, next_selector=None):
        """
        Scrape multiple pages (pagination).

        Args:
            url_template: URL with {page} placeholder, e.g. "https://example.com?page={page}"
                          OR a single URL with next_selector for "Next" button pagination
            pages: Number of pages to scrape
            next_selector: CSS selector for "Next page" button (alternative to url_template)
        """
        all_results = []

        with self._make_browser() as b:
            for page_num in range(1, pages + 1):
                if "{page}" in url_template:
                    url = url_template.format(page=page_num)
                    b.goto(url, settle=3)
                elif page_num == 1:
                    b.goto(url_template, settle=3)
                else:
                    # Click next button
                    if next_selector:
                        try:
                            HumanBehavior.human_click(b.page, next_selector)
                            HumanBehavior.random_delay(2, 4)
                        except Exception:
                            print(f"  No more pages after page {page_num - 1}", file=sys.stderr)
                            break
                    else:
                        break

                # Scroll to load
                for _ in range(2):
                    HumanBehavior.human_scroll(b.page, "down", 500)
                    HumanBehavior.random_delay(0.5, 1.5)

                if selector:
                    page_data = self._extract_by_selector(b, selector, fields)
                else:
                    page_data = self._extract_smart(b, b.page.url)

                if isinstance(page_data, list):
                    all_results.extend(page_data)
                else:
                    all_results.append(page_data)

                print(f"  Page {page_num}: {len(page_data) if isinstance(page_data, list) else 1} items", file=sys.stderr)
                HumanBehavior.between_posts_delay()

        return all_results


# ── Directory Presets ───────────────────────────────────────

PRESETS = {}


def preset(name):
    """Decorator to register a directory preset."""
    def wrapper(fn):
        PRESETS[name] = fn
        return fn
    return wrapper


@preset("google-maps")
def scrape_google_maps(query, location=None, pages=1, headless=True, **kwargs):
    """Scrape Google Maps search results."""
    search = f"{query} {location}" if location else query
    url = f"https://www.google.com/maps/search/{quote_plus(search)}"

    scraper = UniversalScraper(headless=headless)
    with scraper._make_browser() as b:
        b.goto(url, settle=5)

        results = []
        for _ in range(pages):
            # Scroll the results panel
            b.evaluate("""
                () => {
                    const panel = document.querySelector('[role="feed"], .m6QErb');
                    if (panel) panel.scrollBy(0, 2000);
                }
            """)
            HumanBehavior.random_delay(2, 4)

        # Extract listings
        results = b.evaluate("""
            () => {
                const items = [];
                const cards = document.querySelectorAll('[data-result-index], .Nv2PK, a[href*="/maps/place/"]');

                cards.forEach(card => {
                    const name = card.querySelector('.qBF1Pd, .fontHeadlineSmall, [class*="title"]');
                    const rating = card.querySelector('.MW4etd, [class*="rating"]');
                    const reviews = card.querySelector('.UY7F9, [class*="review"]');
                    const category = card.querySelector('.W4Efsd:first-of-type, [class*="category"]');
                    const address = card.querySelector('.W4Efsd:nth-of-type(2), [class*="address"]');
                    const phone = card.querySelector('[data-tooltip*="+"], [class*="phone"]');
                    const link = card.querySelector('a[href*="/maps/place/"]');

                    if (name) {
                        items.push({
                            name: name.textContent.trim(),
                            rating: rating ? rating.textContent.trim() : '',
                            reviews: reviews ? reviews.textContent.trim().replace(/[()]/g, '') : '',
                            category: category ? category.textContent.trim() : '',
                            address: address ? address.textContent.trim() : '',
                            phone: phone ? phone.textContent.trim() : '',
                            maps_url: link ? link.href : '',
                        });
                    }
                });
                return items;
            }
        """)

        print(f"Google Maps: Found {len(results)} businesses", file=sys.stderr)
        return results


@preset("yellowpages")
def scrape_yellowpages(query, location=None, pages=1, headless=True, **kwargs):
    """Scrape YellowPages.com listings."""
    loc = quote_plus(location or "United States")
    q = quote_plus(query)
    results = []

    scraper = UniversalScraper(headless=headless)
    for page_num in range(1, pages + 1):
        url = f"https://www.yellowpages.com/search?search_terms={q}&geo_location_terms={loc}&page={page_num}"

        with scraper._make_browser() as b:
            b.goto(url, settle=3)
            for _ in range(2):
                HumanBehavior.human_scroll(b.page, "down", 600)
                HumanBehavior.random_delay(0.5, 1)

            page_results = b.evaluate("""
                () => {
                    const items = [];
                    const cards = document.querySelectorAll('.result, .search-results .srp-listing');

                    cards.forEach(card => {
                        const name = card.querySelector('.business-name, a.business-name');
                        const phone = card.querySelector('.phones, .phone');
                        const address = card.querySelector('.adr, .street-address');
                        const categories = card.querySelector('.categories, .links');
                        const website = card.querySelector('a.track-visit-website, a[href*="website"]');
                        const rating = card.querySelector('.ratings .count, .result-rating');
                        const link = card.querySelector('a.business-name');

                        if (name) {
                            items.push({
                                name: name.textContent.trim(),
                                phone: phone ? phone.textContent.trim() : '',
                                address: address ? address.textContent.trim() : '',
                                categories: categories ? categories.textContent.trim() : '',
                                website: website ? website.href : '',
                                rating: rating ? rating.textContent.trim() : '',
                                yp_url: link ? link.href : '',
                            });
                        }
                    });
                    return items;
                }
            """)

            results.extend(page_results)
            print(f"  YellowPages page {page_num}: {len(page_results)} listings", file=sys.stderr)
            HumanBehavior.between_posts_delay()

    return results


@preset("justdial")
def scrape_justdial(query, location=None, pages=1, headless=True, **kwargs):
    """Scrape JustDial.com (India) listings."""
    loc = (location or "delhi").lower().replace(" ", "-")
    q = query.lower().replace(" ", "-")
    url = f"https://www.justdial.com/{loc}/{q}"

    scraper = UniversalScraper(headless=headless)
    with scraper._make_browser() as b:
        b.goto(url, settle=4)
        for _ in range(pages * 3):
            HumanBehavior.human_scroll(b.page, "down", 800)
            HumanBehavior.random_delay(1, 2)

        results = b.evaluate("""
            () => {
                const items = [];
                const cards = document.querySelectorAll(
                    '.resultbox_info, .cntanr, [class*="resultbox"], .store-details'
                );

                cards.forEach(card => {
                    const name = card.querySelector(
                        '.resultbox_title_anchor, .lng_cont_name, [class*="title"] a'
                    );
                    const phone = card.querySelector(
                        '.callcontent, [class*="phone"], [class*="contact"]'
                    );
                    const address = card.querySelector(
                        '.resultbox_address, .cont_sw_addr, [class*="address"]'
                    );
                    const rating = card.querySelector(
                        '.resultbox_totalrate, .green-box, [class*="rating"]'
                    );
                    const category = card.querySelector('.resultbox_byline, [class*="category"]');

                    if (name) {
                        items.push({
                            name: name.textContent.trim(),
                            phone: phone ? phone.textContent.trim() : '',
                            address: address ? address.textContent.trim() : '',
                            rating: rating ? rating.textContent.trim() : '',
                            category: category ? category.textContent.trim() : '',
                            jd_url: name.href || '',
                        });
                    }
                });
                return items;
            }
        """)

        print(f"JustDial: Found {len(results)} listings", file=sys.stderr)
        return results


@preset("indiamart")
def scrape_indiamart(query, location=None, pages=1, headless=True, **kwargs):
    """Scrape IndiaMART.com supplier listings."""
    q = quote_plus(query)
    url = f"https://dir.indiamart.com/search.mp?ss={q}"
    if location:
        url += f"&cq={quote_plus(location)}"

    scraper = UniversalScraper(headless=headless)
    with scraper._make_browser() as b:
        b.goto(url, settle=4)
        for _ in range(pages * 2):
            HumanBehavior.human_scroll(b.page, "down", 700)
            HumanBehavior.random_delay(1, 2)

        results = b.evaluate("""
            () => {
                const items = [];
                const cards = document.querySelectorAll('.prd-card, .lsn, [class*="supplier"]');

                cards.forEach(card => {
                    const name = card.querySelector('.lcname, .company-name, [class*="compname"]');
                    const product = card.querySelector('.prd-name, [class*="product"]');
                    const price = card.querySelector('.prc, [class*="price"]');
                    const location = card.querySelector('.clg, [class*="location"], [class*="city"]');
                    const link = card.querySelector('a[href*="indiamart.com"]');

                    if (name || product) {
                        items.push({
                            company: name ? name.textContent.trim() : '',
                            product: product ? product.textContent.trim() : '',
                            price: price ? price.textContent.trim() : '',
                            location: location ? location.textContent.trim() : '',
                            url: link ? link.href : '',
                        });
                    }
                });
                return items;
            }
        """)

        print(f"IndiaMART: Found {len(results)} suppliers", file=sys.stderr)
        return results


@preset("yelp")
def scrape_yelp(query, location=None, pages=1, headless=True, **kwargs):
    """Scrape Yelp business listings."""
    results = []
    scraper = UniversalScraper(headless=headless)

    for page_num in range(pages):
        offset = page_num * 10
        q = quote_plus(query)
        loc = quote_plus(location or "")
        url = f"https://www.yelp.com/search?find_desc={q}&find_loc={loc}&start={offset}"

        with scraper._make_browser() as b:
            b.goto(url, settle=3)
            for _ in range(2):
                HumanBehavior.human_scroll(b.page, "down", 500)
                HumanBehavior.random_delay(0.5, 1)

            page_results = b.evaluate("""
                () => {
                    const items = [];
                    const cards = document.querySelectorAll(
                        '[data-testid="serp-ia-card"], .container__09f24__FeTO6, ' +
                        '.businessName__09f24, li[class*="border"]'
                    );

                    cards.forEach(card => {
                        const name = card.querySelector(
                            'a[href*="/biz/"] span, [class*="businessName"] a'
                        );
                        const rating = card.querySelector('[aria-label*="star"], [class*="rating"]');
                        const reviews = card.querySelector('[class*="reviewCount"]');
                        const category = card.querySelector('[class*="priceCategory"], [class*="category"]');
                        const address = card.querySelector('[class*="secondaryAttributes"]');

                        if (name) {
                            items.push({
                                name: name.textContent.trim(),
                                rating: rating ? (rating.getAttribute('aria-label') || rating.textContent).trim() : '',
                                reviews: reviews ? reviews.textContent.trim() : '',
                                category: category ? category.textContent.trim() : '',
                                address: address ? address.textContent.trim() : '',
                                yelp_url: name.closest('a') ? name.closest('a').href : '',
                            });
                        }
                    });
                    return items;
                }
            """)

            results.extend(page_results)
            print(f"  Yelp page {page_num + 1}: {len(page_results)} listings", file=sys.stderr)
            HumanBehavior.between_posts_delay()

    return results


@preset("indeed")
def scrape_indeed(query, location=None, pages=1, headless=True, **kwargs):
    """Scrape Indeed job listings."""
    results = []
    scraper = UniversalScraper(headless=headless)

    for page_num in range(pages):
        start = page_num * 10
        q = quote_plus(query)
        url = f"https://www.indeed.com/jobs?q={q}&start={start}"
        if location:
            url += f"&l={quote_plus(location)}"

        with scraper._make_browser() as b:
            b.goto(url, settle=4)
            for _ in range(2):
                HumanBehavior.human_scroll(b.page, "down", 500)
                HumanBehavior.random_delay(1, 2)

            page_results = b.evaluate("""
                () => {
                    const items = [];
                    const cards = document.querySelectorAll(
                        '.job_seen_beacon, .jobsearch-ResultsList > li, [data-jk]'
                    );

                    cards.forEach(card => {
                        const title = card.querySelector(
                            '.jobTitle a, h2.jobTitle span, [data-testid="jobTitle"]'
                        );
                        const company = card.querySelector(
                            '.companyName, [data-testid="company-name"], .company_location .companyName'
                        );
                        const location = card.querySelector(
                            '.companyLocation, [data-testid="text-location"]'
                        );
                        const salary = card.querySelector(
                            '.salary-snippet-container, [class*="salary"], .metadata .attribute_snippet'
                        );
                        const snippet = card.querySelector('.job-snippet, [class*="snippet"]');
                        const link = card.querySelector('a[href*="/viewjob"], a[data-jk]');

                        if (title) {
                            items.push({
                                title: title.textContent.trim(),
                                company: company ? company.textContent.trim() : '',
                                location: location ? location.textContent.trim() : '',
                                salary: salary ? salary.textContent.trim() : '',
                                snippet: snippet ? snippet.textContent.trim().substring(0, 200) : '',
                                indeed_url: link ? 'https://www.indeed.com' + (link.getAttribute('href') || '') : '',
                            });
                        }
                    });
                    return items;
                }
            """)

            results.extend(page_results)
            print(f"  Indeed page {page_num + 1}: {len(page_results)} jobs", file=sys.stderr)
            HumanBehavior.between_posts_delay()

    return results


# ── Output Formatters ───────────────────────────────────────

def save_results(results, output_path, fmt="json"):
    """Save results to file."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if fmt == "csv" and isinstance(results, list) and results:
        keys = set()
        for r in results:
            if isinstance(r, dict):
                keys.update(r.keys())
        keys = sorted(keys)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in results:
                if isinstance(r, dict):
                    writer.writerow({k: r.get(k, "") for k in keys})
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_path}", file=sys.stderr)


# ── CLI ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Universal Web Scraper — works on any website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Presets: google-maps, yellowpages, justdial, indiamart, yelp, indeed

Examples:
  python3 universal_scraper.py https://example.com
  python3 universal_scraper.py google-maps --query "plumbers in Austin TX"
  python3 universal_scraper.py yellowpages --query "dentists" --location "New York" --pages 3
  python3 universal_scraper.py indeed --query "AI engineer" --location "Remote" --pages 2
  python3 universal_scraper.py https://example.com --selector ".product-card" --format csv
""",
    )
    parser.add_argument("target", help="URL to scrape OR preset name")
    parser.add_argument("--query", "-q", help="Search query (for presets)")
    parser.add_argument("--location", "-l", help="Location filter (for presets)")
    parser.add_argument("--pages", type=int, default=1, help="Pages to scrape")
    parser.add_argument("--selector", "-s", help="CSS selector for targeted extraction")
    parser.add_argument("--fields", "-f", help="Comma-separated field names for selector mode")
    parser.add_argument("--mode", choices=["smart", "full", "selector"], default="smart")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--visible", action="store_true", help="Show browser")
    args = parser.parse_args()

    headless = not args.visible

    # Check if target is a preset
    if args.target in PRESETS:
        if not args.query:
            print(f"Error: --query is required for preset '{args.target}'", file=sys.stderr)
            sys.exit(1)
        results = PRESETS[args.target](
            query=args.query, location=args.location,
            pages=args.pages, headless=headless,
        )
    elif args.target.startswith("http"):
        scraper = UniversalScraper(headless=headless)
        if args.selector:
            args.mode = "selector"
        results = scraper.scrape_url(
            args.target, mode=args.mode, selector=args.selector,
            fields=args.fields, scroll_pages=args.pages,
        )
    else:
        print(f"Error: '{args.target}' is not a URL or known preset", file=sys.stderr)
        print(f"Available presets: {', '.join(PRESETS.keys())}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        save_results(results, args.output, fmt=args.format)
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
