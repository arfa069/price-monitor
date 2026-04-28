"""Boss Zhipin platform adapter for job list crawling.

Strategy: curl_cffi impersonates Chrome 124 at TLS level to call the search
API (wapi/zpgeek/search/joblist.json). Cookies are read from the CDP browser
via minimal raw WebSocket (2 CDP commands, avoids anti-bot detection) and
persisted to disk so subsequent crawls don't need the browser at all.
"""

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import websockets
from curl_cffi.requests import Session as CffiSession

from app.platforms.base import BasePlatformAdapter

logger = logging.getLogger(__name__)

MAX_PAGES = 3
SEARCH_API_PATH = "/wapi/zpgeek/search/joblist.json"
DETAIL_API_PATH = "/wapi/zpgeek/job/detail.json"
BASE_URL = "https://www.zhipin.com"
CDP_BASE = "http://127.0.0.1:9222"
COOKIE_FILE = Path(__file__).resolve().parent / ".boss_cookies.json"


class BossZhipinAdapter(BasePlatformAdapter):
    """Adapter for Boss Zhipin job search list crawling.

    Cookie lifecycle:
    1. Read cookies from CDP browser via raw WebSocket (< 0.1s, non-destructive).
    2. Persist to disk after each successful crawl.
    3. Subsequent crawls use disk cookies (no browser needed).
    4. CffiSession auto-updates cookies from API Set-Cookie headers.
    5. When cookies expire: re-read from CDP browser (page must be open, past captcha).
    """

    def __init__(self):
        super().__init__()

    # ── Public interface ──────────────────────────────────────────────

    async def extract_price(self, page) -> dict[str, Any]:
        raise NotImplementedError

    async def extract_title(self, page) -> str:
        raise NotImplementedError

    # ── Cookie acquisition via raw WebSocket CDP ───────────────────────

    @staticmethod
    async def _get_cookies_via_raw_cdp() -> dict[str, str]:
        """Read Boss cookies via raw WebSocket CDP — only 2 commands."""
        ws_url = await BossZhipinAdapter._find_page_ws()
        if not ws_url:
            return {}

        try:
            async with websockets.connect(ws_url, max_size=2 ** 24) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
                await asyncio.wait_for(ws.recv(), timeout=2)

                await ws.send(json.dumps({
                    "id": 2, "method": "Network.getCookies",
                    "params": {"urls": ["https://www.zhipin.com/"]},
                }))
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                result = json.loads(raw)

            cookies = {}
            for c in result.get("result", {}).get("cookies", []):
                cookies[c["name"]] = c["value"]
            logger.debug("Raw CDP: %d cookies", len(cookies))
            return cookies

        except Exception as e:
            logger.warning("Raw CDP cookie read failed: %s", e)
            return {}

    @staticmethod
    async def _refresh_cookies_via_new_tab() -> bool:
        """Silently open Boss homepage in a new CDP tab, then close it.

        The page load triggers Set-Cookie headers that refresh the browser's
        cookie store. No visible window — the tab is created and destroyed
        via CDP protocol, not OS window management.
        """
        import http.client

        try:
            # Get browser-level WebSocket URL
            conn = http.client.HTTPConnection("127.0.0.1", 9222, timeout=3)
            conn.request("GET", "/json/version")
            data = json.loads(conn.getresponse().read())
            browser_ws = data.get("webSocketDebuggerUrl")
            if not browser_ws:
                return False

            async with websockets.connect(browser_ws, max_size=2 ** 24) as ws:
                await ws.send(json.dumps({
                    "id": 1, "method": "Target.createTarget",
                    "params": {"url": "https://www.zhipin.com/?ka=header-home"},
                }))
                result = json.loads(await ws.recv())
                target_id = result["result"]["targetId"]

            # Let the page load and Set-Cookie propagate
            await asyncio.sleep(5)

            # Close the tab
            async with websockets.connect(browser_ws, max_size=2 ** 24) as ws:
                await ws.send(json.dumps({
                    "id": 2, "method": "Target.closeTarget",
                    "params": {"targetId": target_id},
                }))
                await ws.recv()

            logger.debug("Cookie refresh via new tab completed")
            return True

        except Exception as e:
            logger.warning("New-tab cookie refresh failed: %s", e)
            return False

    @staticmethod
    async def _find_page_ws() -> str | None:
        """Find a page's WebSocket CDP URL — prefers Boss, falls back to any."""
        import http.client
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 9222, timeout=3)
            conn.request("GET", "/json")
            resp = conn.getresponse()
            targets = json.loads(resp.read())

            # Prefer a Boss page (most likely to have fresh zhipin cookies)
            for t in targets:
                url = t.get("url", "")
                if "zhipin" in url and "socket" not in url:
                    return t["webSocketDebuggerUrl"]

            # Fall back to any page with a debugger URL
            for t in targets:
                if "webSocketDebuggerUrl" in t:
                    return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        return None

    # ── Cookie persistence ─────────────────────────────────────────────

    @staticmethod
    def _load_cookies() -> dict[str, str]:
        try:
            if COOKIE_FILE.exists():
                return json.loads(COOKIE_FILE.read_text())
        except Exception:
            pass
        return {}

    @staticmethod
    def _save_cookies(cffi_session: CffiSession) -> None:
        try:
            COOKIE_FILE.write_text(json.dumps(
                cffi_session.cookies.get_dict()
            ))
        except Exception:
            pass

    @staticmethod
    def _refresh_via_homepage(session: CffiSession) -> None:
        try:
            session.get(
                "https://www.zhipin.com/?ka=header-home",
                impersonate="chrome124",
                headers={"Referer": "https://www.zhipin.com/"},
            )
        except Exception:
            pass

    # ── Crawl ───────────────────────────────────────────────────────────

    async def _acquire_cookies(self, session: CffiSession) -> bool:
        """Populate session with working cookies."""
        test_url = (
            f"{BASE_URL}{SEARCH_API_PATH}"
            "?scene=1&query=test&city=101280100&page=1&pageSize=1"
        )

        def _test(s) -> bool:
            try:
                resp = s.get(test_url, impersonate="chrome124",
                            headers={"Referer": "https://www.zhipin.com/"})
                return resp.status_code == 200 and resp.json().get("code") == 0
            except Exception:
                return False

        # 1. Disk cache
        saved = self._load_cookies()
        if saved:
            session.cookies.update(saved)
            if _test(session):
                logger.info("Using cached cookies from disk")
                return True
            logger.info("Cached cookies expired, trying CDP")

        # 2. Raw WebSocket CDP (non-destructive, <0.1s)
        cdp_cookies = await self._get_cookies_via_raw_cdp()
        if cdp_cookies:
            session.cookies.update(cdp_cookies)
            if _test(session):
                logger.info("Using CDP cookies (%d)", len(cdp_cookies))
                return True
            logger.info("CDP cookies expired")

        # 3. Create a new tab to Boss homepage — loads fresh cookies
        #    silently via CDP Target.createTarget, then closes it.
        if await self._refresh_cookies_via_new_tab():
            fresh = await self._get_cookies_via_raw_cdp()
            if fresh:
                session.cookies.clear()
                session.cookies.update(fresh)
                if _test(session):
                    logger.info("Cookies refreshed via new tab (%d)", len(fresh))
                    return True

        # 4. Homepage refresh (last resort)
        self._refresh_via_homepage(session)
        if _test(session):
            logger.info("Cookies acquired via homepage refresh")
            return True

        return False

    async def crawl(self, url: str) -> dict[str, Any]:
        """Crawl a Boss Zhipin job search via curl_cffi + persistent cookies."""
        try:
            session = CffiSession()

            if not await self._acquire_cookies(session):
                return {
                    "success": False,
                    "error": (
                        "No valid cookies. Please open "
                        "https://www.zhipin.com in your browser, "
                        "complete captcha if shown, then retry."
                    ),
                }

            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            params.pop("page", None)
            params.pop("pageSize", None)
            params.setdefault("scene", ["1"])

            all_jobs: list[dict] = []
            pages_fetched = 0

            for page_num in range(1, MAX_PAGES + 1):
                # Refresh cookies before each page — mirrors the article's
                # update_cookies() pattern. Page 1 already has cookies from
                # _acquire_cookies; subsequent pages pull fresh CDP cookies.
                if page_num > 1:
                    fresh = await self._get_cookies_via_raw_cdp()
                    if fresh:
                        session.cookies.update(fresh)

                params["page"] = [str(page_num)]
                params["pageSize"] = ["15"]
                query = urlencode(params, doseq=True)
                api_url = f"{BASE_URL}{SEARCH_API_PATH}?{query}"

                resp = session.get(
                    api_url,
                    impersonate="chrome124",
                    headers={"Referer": url},
                )

                if resp.status_code != 200:
                    logger.warning("API HTTP %d on page %d", resp.status_code, page_num)
                    break

                data = resp.json()
                if data.get("code") != 0 or "异常" in resp.text:
                    # Refresh cascade: CDP → new-tab → homepage
                    logger.info("API code=%s on page %d, refreshing",
                               data.get("code"), page_num)
                    recovered = False

                    # 1. CDP refresh from existing page
                    fresh = await self._get_cookies_via_raw_cdp()
                    if fresh:
                        session.cookies.update(fresh)
                        resp = session.get(api_url, impersonate="chrome124",
                                          headers={"Referer": url})
                        data = resp.json()
                        if data.get("code") == 0:
                            logger.info("Recovered via CDP refresh")
                            recovered = True

                    # 2. New-tab refresh (silent Target.createTarget)
                    if not recovered and await self._refresh_cookies_via_new_tab():
                        fresh = await self._get_cookies_via_raw_cdp()
                        if fresh:
                            session.cookies.clear()
                            session.cookies.update(fresh)
                            resp = session.get(api_url, impersonate="chrome124",
                                              headers={"Referer": url})
                            data = resp.json()
                            if data.get("code") == 0:
                                logger.info("Recovered via new-tab refresh")
                                recovered = True

                    # 3. Homepage refresh (last resort)
                    if not recovered:
                        self._refresh_via_homepage(session)
                        await asyncio.sleep(2)
                        resp = session.get(api_url, impersonate="chrome124",
                                          headers={"Referer": url})
                        data = resp.json()
                        if data.get("code") != 0:
                            logger.warning("All refreshes failed on page %d", page_num)
                            break
                        logger.info("Recovered via homepage refresh")

                page_jobs = data.get("zpData", {}).get("jobList", [])
                if not page_jobs:
                    break

                all_jobs.extend(page_jobs)
                pages_fetched = page_num

                if not data.get("zpData", {}).get("hasMore"):
                    break

                await asyncio.sleep(random.uniform(2.0, 5.0))

            if all_jobs:
                transformed = self._transform_jobs(all_jobs)
                logger.info("curl_cffi: %d jobs from %d page(s)",
                           len(transformed), pages_fetched)
                self._save_cookies(session)
                return {"success": True, "jobs": transformed, "count": len(transformed)}

            return {"success": False, "error": "No job data from search API"}

        except Exception as e:
            logger.exception("Boss crawl failed")
            return {"success": False, "error": str(e)}

    async def crawl_detail(self, security_id: str) -> dict[str, Any]:
        """Crawl a Boss Zhipin job detail page.

        Args:
            security_id: The securityId from the job list (used for API call).

        Returns:
            {"success": True, "detail": {...}} on success.
            {"success": False, "error": "..."} on failure.
        """
        try:
            session = CffiSession()

            if not await self._acquire_cookies(session):
                return {
                    "success": False,
                    "error": (
                        "No valid cookies. Please open "
                        "https://www.zhipin.com in your browser, "
                        "complete captcha if shown, then retry."
                    ),
                }

            api_url = f"{BASE_URL}{DETAIL_API_PATH}?securityId={security_id}"
            resp = session.get(
                api_url,
                impersonate="chrome124",
                headers={"Referer": f"{BASE_URL}/"},
            )

            if resp.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {resp.status_code}",
                }

            data = resp.json()
            if data.get("code") != 0:
                return {
                    "success": False,
                    "error": f"API code={data.get('code')}: {data.get('message', 'unknown')}",
                }

            job_info = data.get("zpData", {}).get("jobInfo", {})
            brand_info = data.get("zpData", {}).get("brandComInfo", {})

            self._save_cookies(session)

            return {
                "success": True,
                "detail": {
                    "job_id": security_id,
                    "title": job_info.get("jobName", ""),
                    "salary": job_info.get("salaryDesc", ""),
                    "location": job_info.get("locationName", ""),
                    "address": job_info.get("address", ""),
                    "experience": job_info.get("experienceName", ""),
                    "education": job_info.get("degreeName", ""),
                    "description": job_info.get("postDescription", ""),
                    "company": brand_info.get("brandName", ""),
                    "company_stage": brand_info.get("stageName", ""),
                    "company_scale": brand_info.get("scaleName", ""),
                    "company_industry": brand_info.get("industryName", ""),
                },
            }

        except Exception as e:
            logger.exception("Boss detail crawl failed")
            return {"success": False, "error": str(e)}

        # ── Data transformation ────────────────────────────────────────────

    def _transform_jobs(self, raw_jobs: list[dict]) -> list[dict]:
        transformed = []
        for job in raw_jobs:
            job_id = job.get("encryptId") or job.get("securityId") or ""
            encrypt_id = job.get("encryptId") or ""

            transformed.append({
                "job_id": job_id,
                "title": job.get("jobName", ""),
                "company": job.get("brandName", ""),
                "company_id": job.get("encryptBrandId", ""),
                "salary": job.get("salaryDesc", ""),
                "location": job.get("cityName", "") or job.get("areaDistrict", ""),
                "experience": job.get("jobExperience", ""),
                "education": job.get("jobDegree", ""),
                "url": f"https://www.zhipin.com/job_detail/{encrypt_id}.html" if encrypt_id else "",
            })
        return transformed
