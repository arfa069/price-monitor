"""Boss Zhipin platform adapter for job list crawling."""
import asyncio
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.platforms.base import BasePlatformAdapter


class BossZhipinAdapter(BasePlatformAdapter):
    """Adapter for Boss Zhipin job search list crawling.

    Reuses BasePlatformAdapter's CDP browser lifecycle.
    Does NOT use extract_price/title (single-product interface).
    """

    async def extract_price(self, page) -> dict[str, Any]:
        """Not used for job crawler."""
        raise NotImplementedError("BossZhipinAdapter does not support price extraction")

    async def extract_title(self, page) -> str:
        """Not used for job crawler."""
        raise NotImplementedError("BossZhipinAdapter does not support title extraction")

    async def crawl(self, url: str) -> dict[str, Any]:
        """Crawl a boss zhipin job search list page.

        Returns:
            {
                "success": bool,
                "jobs": list[dict],  # extracted job data
                "count": int,
            }
        """
        await self._init_browser()

        try:
            async with asyncio.timeout(90):
                await self._page.goto(url, wait_until="domcontentloaded", timeout=45000)

                # Wait for job card list to appear
                await self._page.wait_for_selector(
                    ".job-list-box .job-card-wrapper",
                    timeout=20000,
                )

                # Scroll to load more jobs (infinite scroll)
                await self._scroll_to_load_more(max_scrolls=5)

                # Extract all job cards
                jobs = await self._extract_jobs(self._page)

                return {
                    "success": True,
                    "jobs": jobs,
                    "count": len(jobs),
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Crawl timeout: page took longer than 90s to respond",
            }
        except PlaywrightTimeoutError as e:
            return {
                "success": False,
                "error": f"Page load timeout: {e}",
            }
        except (ConnectionError, OSError) as e:
            return {
                "success": False,
                "error": f"Network error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
            }
        finally:
            await self._close_browser()

    async def _scroll_to_load_more(self, max_scrolls: int = 5) -> None:
        """Scroll down to trigger lazy loading of more job cards.

        Boss Zhipin uses infinite scroll - each scroll loads ~30 more jobs.
        Terminates early if no new jobs appear after a scroll.
        """
        for _ in range(max_scrolls):
            previous_count = await self._page.evaluate(
                "() => document.querySelectorAll('.job-card-wrapper').length"
            )
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self._page.wait_for_timeout(1500)
            current_count = await self._page.evaluate(
                "() => document.querySelectorAll('.job-card-wrapper').length"
            )
            if current_count == previous_count:
                # No new jobs loaded, stop scrolling
                break

    async def _extract_jobs(self, page) -> list[dict]:
        """Extract job data from all visible job cards using page.evaluate.

        Faster than using Playwright locators one by one.
        """
        return await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('.job-card-wrapper');
                return Array.from(cards).map(card => {
                    // Try to get job_id from data attribute or onclick
                    let jobId = card.getAttribute('data-jobid') || '';
                    if (!jobId) {
                        const link = card.querySelector('a');
                        if (link) {
                            const match = link.href.match(/job_detail\\/([^.]+)/);
                            if (match) jobId = match[1];
                        }
                    }

                    // Get company info
                    let companyId = '';
                    const companyEl = card.querySelector('.company-info');
                    if (companyEl) {
                        const match = companyEl.getAttribute('data-lid') ||
                                      companyEl.getAttribute('data-jobid');
                        if (match) companyId = match;
                    }

                    // Get tags (experience, education)
                    const tagEls = card.querySelectorAll('.tag-list li');
                    const tags = Array.from(tagEls).map(el => el.innerText.trim());

                    // Get salary
                    const salaryEl = card.querySelector('.salary');
                    const salary = salaryEl ? salaryEl.innerText.trim() : '';

                    // Get area
                    const areaEl = card.querySelector('.job-area');
                    const area = areaEl ? areaEl.innerText.trim() : '';

                    // Get job link
                    const linkEl = card.querySelector('a');
                    const jobUrl = linkEl ? linkEl.href : '';

                    return {
                        job_id: jobId,
                        title: (card.querySelector('.job-name') || {}).innerText || '',
                        company: (card.querySelector('.company-name') || {}).innerText || '',
                        company_id: companyId,
                        salary: salary,
                        location: area,
                        experience: tags[0] || '',
                        education: tags[1] || '',
                        url: jobUrl,
                    };
                });
            }
        """)
