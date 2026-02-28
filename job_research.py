#!/usr/bin/env python3
"""
Job Research Script — Browse AI jobs on LinkedIn & Indeed in visible browser.
Extracts what companies are looking for in AI Consultant / AI Lead / AI Architect roles.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))
from linkedin_browser import LinkedInBrowser
from base_browser import BaseBrowser
from human_behavior import HumanBehavior

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

OUTPUT_FILE = "/tmp/ai_job_research.json"

SEARCHES = [
    "AI consultant",
    "AI lead",
    "AI solutions architect",
]


def search_linkedin_jobs(browser, queries, jobs_per_query=5):
    """Search LinkedIn for multiple queries, get details for top jobs."""
    all_jobs = []

    for query in queries:
        print(f"\n{'='*60}")
        print(f"LinkedIn Search: {query}")
        print(f"{'='*60}")

        jobs = browser.search_jobs(query, limit=8)
        HumanBehavior.random_delay(2, 3)

        # Get details for top jobs
        for job in jobs[:jobs_per_query]:
            if not job.get("job_url"):
                continue

            print(f"\n  Opening: {job['title']} at {job['company']}")
            try:
                details = browser.get_job_details(job["job_url"])
                job_data = {
                    "source": "LinkedIn",
                    "query": query,
                    "title": details.get("title") or job.get("title", ""),
                    "company": details.get("company") or job.get("company", ""),
                    "location": details.get("location") or job.get("location", ""),
                    "description": details.get("description", ""),
                    "is_easy_apply": details.get("is_easy_apply", False),
                    "url": job["job_url"],
                }
                all_jobs.append(job_data)
                print(f"    Title: {job_data['title']}")
                print(f"    Company: {job_data['company']}")
                print(f"    Location: {job_data['location']}")
                desc_preview = job_data['description'][:150].replace('\n', ' ')
                print(f"    Preview: {desc_preview}...")
            except Exception as e:
                print(f"    Error getting details: {e}")

            HumanBehavior.between_posts_delay()

    return all_jobs


def search_indeed_jobs(browser, queries, jobs_per_query=5):
    """Search Indeed for multiple queries, extract job cards + details."""
    all_jobs = []

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Indeed Search: {query}")
        print(f"{'='*60}")

        url = f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l=Remote"
        browser.goto(url, settle=4)

        # Scroll to load results
        for _ in range(3):
            HumanBehavior.human_scroll(browser.page, "down", 400)
            HumanBehavior.random_delay(1, 2)

        # Extract job cards
        job_cards = browser.evaluate("""
            () => {
                const results = [];
                const cards = document.querySelectorAll(
                    '.job_seen_beacon, .jobsearch-ResultsList .result, ' +
                    '[data-jk], .tapItem, .resultContent'
                );
                for (let i = 0; i < Math.min(cards.length, 15); i++) {
                    const card = cards[i];
                    const titleEl = card.querySelector('h2 a, .jobTitle a, h2 span[title]');
                    const companyEl = card.querySelector('[data-testid="company-name"], .companyName, .company');
                    const locationEl = card.querySelector('[data-testid="text-location"], .companyLocation, .location');
                    const snippetEl = card.querySelector('.job-snippet, .underShelfFooter, td.snip');
                    const link = card.querySelector('a[href*="/viewjob"], a[data-jk], h2 a');

                    if (titleEl) {
                        results.push({
                            title: titleEl.textContent.trim(),
                            company: companyEl ? companyEl.textContent.trim() : '',
                            location: locationEl ? locationEl.textContent.trim() : '',
                            snippet: snippetEl ? snippetEl.textContent.trim() : '',
                            url: link ? link.href : '',
                        });
                    }
                }
                return results;
            }
        """)

        print(f"  Found {len(job_cards)} job cards")

        # Click into top jobs to get full descriptions
        for card in job_cards[:jobs_per_query]:
            if not card.get("url"):
                continue

            print(f"\n  Opening: {card['title']} at {card['company']}")
            try:
                browser.goto(card["url"], settle=3)
                HumanBehavior.human_scroll(browser.page, "down", 300)
                HumanBehavior.random_delay(1, 2)

                # Extract full job description
                description = browser.evaluate("""
                    () => {
                        const desc = document.querySelector(
                            '#jobDescriptionText, .jobsearch-JobComponent-description, ' +
                            '.jobsearch-jobDescriptionText, [id*="jobDescription"]'
                        );
                        return desc ? desc.textContent.trim().substring(0, 2000) : '';
                    }
                """)

                job_data = {
                    "source": "Indeed",
                    "query": query,
                    "title": card["title"],
                    "company": card["company"],
                    "location": card["location"],
                    "description": description or card.get("snippet", ""),
                    "url": card["url"],
                }
                all_jobs.append(job_data)
                print(f"    Company: {job_data['company']}")
                print(f"    Location: {job_data['location']}")
                desc_preview = job_data['description'][:150].replace('\n', ' ')
                print(f"    Preview: {desc_preview}...")
            except Exception as e:
                print(f"    Error: {e}")

            HumanBehavior.between_posts_delay()

    return all_jobs


def main():
    all_results = []

    # ── Phase 1: LinkedIn (needs auth) ──
    print("\n" + "="*60)
    print("PHASE 1: LinkedIn Job Search (visible browser)")
    print("="*60)

    try:
        lb = LinkedInBrowser(headless=False)
        lb.start()
        linkedin_jobs = search_linkedin_jobs(lb, SEARCHES, jobs_per_query=2)
        all_results.extend(linkedin_jobs)
        lb.stop()
        print(f"\nLinkedIn: {len(linkedin_jobs)} jobs collected")
    except Exception as e:
        print(f"LinkedIn error: {e}")

    HumanBehavior.random_delay(2, 4)

    # ── Phase 2: Indeed (no auth needed) ──
    print("\n" + "="*60)
    print("PHASE 2: Indeed Job Search (visible browser)")
    print("="*60)

    try:
        viewport = HumanBehavior.random_viewport()
        bb = BaseBrowser(headless=False, viewport=viewport)
        bb.start()
        indeed_jobs = search_indeed_jobs(bb, SEARCHES, jobs_per_query=2)
        all_results.extend(indeed_jobs)
        bb.stop()
        print(f"\nIndeed: {len(indeed_jobs)} jobs collected")
    except Exception as e:
        print(f"Indeed error: {e}")

    # ── Save results ──
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nAll results saved to {OUTPUT_FILE}")
    print(f"Total jobs collected: {len(all_results)}")

    # ── Quick Summary ──
    print("\n" + "="*60)
    print("QUICK SUMMARY")
    print("="*60)
    for job in all_results:
        print(f"\n[{job['source']}] {job['title']}")
        print(f"  Company: {job['company']} | Location: {job['location']}")
        if job['description']:
            print(f"  Preview: {job['description'][:200].replace(chr(10), ' ')}...")


if __name__ == "__main__":
    main()
