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
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import websockets
from curl_cffi.requests import Session as CffiSession

from app.platforms.base import BasePlatformAdapter

logger = logging.getLogger(__name__)

MAX_PAGES = 3
PAGE_SIZE = 45
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
        self._session: CffiSession | None = None
        self._cookies_acquired_at: float = 0

    def _get_session(self) -> CffiSession:
        if self._session is None:
            self._session = CffiSession()
        return self._session

    async def _ensure_cookies(self) -> bool:
        """Ensure the adapter has valid cookies.

        Returns True if cookies are fresh (acquired within 5 min) or
        successfully refreshed.
        """
        if self._cookies_acquired_at and time.time() - self._cookies_acquired_at < 300:
            return True
        if await self._acquire_cookies(self._get_session()):
            return True
        return False

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
    async def _quick_refresh_cookies() -> bool:
        """快速刷新 cookies：开新 tab 加载 Boss 主页，等待后关闭，从原 CDP 读取 cookies。

        用于 cookies 过期时快速刷新。
        """
        import http.client

        target_id = None
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 9222, timeout=3)
            conn.request("GET", "/json/version")
            data = json.loads(conn.getresponse().read())
            browser_ws = data.get("webSocketDebuggerUrl")
            conn.close()
            if not browser_ws:
                return False

            # 开新 tab 到 Boss 主页
            async with websockets.connect(browser_ws, max_size=2 ** 24) as ws:
                await ws.send(json.dumps({
                    "id": 1, "method": "Target.createTarget",
                    "params": {"url": "https://www.zhipin.com/?ka=header-home"},
                }))
                result = json.loads(await ws.recv())
                target_id = result["result"]["targetId"]

            # 等待 cookies 生效
            await asyncio.sleep(5)

            return True

        except Exception as e:
            logger.warning("Quick cookie refresh failed: %s", e)
            return False

        finally:
            # 确保关闭 tab
            if target_id:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", 9222, timeout=3)
                    conn.request("GET", "/json/version")
                    data = json.loads(conn.getresponse().read())
                    browser_ws = data.get("webSocketDebuggerUrl")
                    conn.close()
                    if browser_ws:
                        async with websockets.connect(browser_ws, max_size=2 ** 24) as ws:
                            await ws.send(json.dumps({
                                "id": 99, "method": "Target.closeTarget",
                                "params": {"targetId": target_id},
                            }))
                            await asyncio.wait_for(ws.recv(), timeout=2)
                except Exception as e:
                    logger.warning("Failed to close tab: %s", e)

    @staticmethod
    async def _find_page_ws() -> str | None:
        """Find a page's WebSocket CDP URL — prefers Boss, falls back to any."""
        import http.client
        conn = None
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 9222, timeout=3)
            conn.request("GET", "/json")
            resp = conn.getresponse()
            targets = json.loads(resp.read())
            conn.close()

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
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
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
            "?scene=1&query=python&city=101280100&page=1&pageSize=15"
        )

        def _test(s) -> bool:
            try:
                resp = s.get(test_url, impersonate="chrome124",
                            headers={"Referer": "https://www.zhipin.com/web/geek/jobs?query=python&city=101280100"})
                return resp.status_code == 200 and resp.json().get("code") == 0
            except Exception:
                return False

        # 1. Disk cache — 不开 tab，不消耗 Cookie
        saved = self._load_cookies()
        if saved:
            session.cookies.update(saved)
            if _test(session):
                logger.info("Using cached cookies from disk")
                self._cookies_acquired_at = time.time()
                return True
            logger.info("Cached cookies expired, trying CDP")
            session.cookies.clear()

        # 2. Raw WebSocket CDP (non-destructive, <0.1s)
        cdp_cookies = await self._get_cookies_via_raw_cdp()
        if cdp_cookies:
            session.cookies.update(cdp_cookies)
            if _test(session):
                logger.info("Using CDP cookies (%d)", len(cdp_cookies))
                self._cookies_acquired_at = time.time()
                return True
            logger.info("CDP cookies expired")
            session.cookies.clear()

        # 3. 新 tab 刷新搜索页 cookies（快速开闭，约 5 秒）
        if await self._quick_refresh_cookies():
            fresh = await self._get_cookies_via_raw_cdp()
            if fresh:
                session.cookies.update(fresh)
                if _test(session):
                    logger.info("Cookies refreshed via quick new-tab")
                    self._cookies_acquired_at = time.time()
                    return True
            session.cookies.clear()

        # 4. 主页刷新保底
        self._refresh_via_homepage(session)
        if _test(session):
            logger.info("Cookies acquired via homepage refresh")
            self._cookies_acquired_at = time.time()
            return True

        return False

    async def crawl(self, url: str) -> dict[str, Any]:
        """Crawl a Boss Zhipin job search via curl_cffi + persistent cookies."""
        try:
            session = self._get_session()

            if not await self._ensure_cookies():
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
                params["page"] = [str(page_num)]
                params["pageSize"] = [PAGE_SIZE]
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
                    logger.warning("API code=%s on page %d", data.get("code"), page_num)
                    break

                page_jobs = data.get("zpData", {}).get("jobList", [])
                if not page_jobs:
                    break

                all_jobs.extend(page_jobs)
                pages_fetched = page_num

                if not data.get("zpData", {}).get("hasMore"):
                    break

                await asyncio.sleep(random.uniform(3.0, 6.0))

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
            session = self._get_session()

            if not await self._ensure_cookies():
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
                # If cookies were just acquired, don't retry — the error
                # isn't a stale-cookie issue.
                logger.warning("Detail API code=%s for securityId=%s",
                              data.get("code"), security_id[:8])
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
