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
        """Ensure the adapter has valid cookies for search API."""
        if self._cookies_acquired_at and time.time() - self._cookies_acquired_at < 300:
            logger.warning("_ensure_cookies: cache hit, returning True")
            return True
        logger.warning("_ensure_cookies: calling _acquire_cookies")
        if await self._acquire_cookies(self._get_session()):
            logger.warning("_ensure_cookies: _acquire_cookies succeeded")
            return True
        logger.warning("_ensure_cookies: _acquire_cookies FAILED")
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
    async def _quick_refresh_cookies() -> dict[str, str]:
        """直接开后台 tab 到搜索页以获取新 __zp_stoken__。

        Target.createTarget 直接到搜索 URL，服务端响应 Set-Cookie。
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
                return {}

            search_url = (
                "https://www.zhipin.com/web/geek/jobs"
                "?query=python&city=101280100"
            )
            async with websockets.connect(browser_ws, max_size=2 ** 24) as ws:
                await ws.send(json.dumps({
                    "id": 1, "method": "Target.createTarget",
                    "params": {"url": search_url, "background": True},
                }))
                result = json.loads(await ws.recv())
                target_id = result["result"]["targetId"]

            # 等 HTTP 响应 + 浏览器处理 Set-Cookie
            await asyncio.sleep(2.5)

            target_ws = await BossZhipinAdapter._find_target_ws(target_id)
            if not target_ws:
                return {}

            cookies = {}
            async with websockets.connect(target_ws, max_size=2 ** 24) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
                await asyncio.wait_for(ws.recv(), timeout=2)
                await ws.send(json.dumps({
                    "id": 2, "method": "Network.getCookies",
                    "params": {"urls": ["https://www.zhipin.com/"]},
                }))
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(raw)

                for c in data.get("result", {}).get("cookies", []):
                    cookies[c["name"]] = c["value"]

            st_new = cookies.get("__zp_stoken__", "<missing>")
            logger.warning("quick-refresh: %d cookies, stoken=%s", len(cookies),
                       st_new[:24] if len(st_new) > 24 else st_new)
            return cookies

        except Exception as e:
            logger.warning("quick-refresh FAILED: %s", e)
            return {}
        finally:
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
                except Exception:
                    pass

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

            for t in targets:
                url = t.get("url", "")
                if "zhipin" in url and "socket" not in url:
                    return t["webSocketDebuggerUrl"]

            for t in targets:
                if "webSocketDebuggerUrl" in t:
                    return t["webSocketDebuggerUrl"]
        except Exception:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return None

    @staticmethod
    async def _find_target_ws(target_id: str) -> str | None:
        """根据 targetId 查找 CDP WebSocket URL。"""
        import http.client

        conn = None
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 9222, timeout=3)
            conn.request("GET", "/json")
            resp = conn.getresponse()
            targets = json.loads(resp.read())
            conn.close()
            for t in targets:
                if t.get("id") == target_id:
                    return t.get("webSocketDebuggerUrl")
        except Exception:
            if conn:
                try:
                    conn.close()
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
        """直接加载 cookie，不做搜索 API 测试（测试消耗 __zp_stoken__）。"""
        logger.warning("_acquire_cookies: START (no-test mode)")

        # 1. CDP
        cdp_cookies = await self._get_cookies_via_raw_cdp()
        if cdp_cookies and cdp_cookies.get("__zp_stoken__"):
            for k, v in cdp_cookies.items():
                session.cookies.set(k, v, domain=".zhipin.com", path="/")
            logger.warning("_acquire_cookies: using CDP cookies")
            self._cookies_acquired_at = time.time()
            return True

        # 2. 磁盘缓存
        saved = self._load_cookies()
        if saved and saved.get("__zp_stoken__"):
            for k, v in saved.items():
                session.cookies.set(k, v, domain=".zhipin.com", path="/")
            logger.warning("_acquire_cookies: using disk cache")
            self._cookies_acquired_at = time.time()
            return True

        # 3. 快速刷新
        fresh = await self._quick_refresh_cookies()
        if fresh and fresh.get("__zp_stoken__"):
            for k, v in fresh.items():
                session.cookies.set(k, v, domain=".zhipin.com", path="/")
            logger.warning("_acquire_cookies: using quick-refresh")
            self._cookies_acquired_at = time.time()
            return True

        # 4. 主页刷新保底
        self._refresh_via_homepage(session)
        if session.cookies.get("__zp_stoken__"):
            logger.warning("_acquire_cookies: using homepage refresh")
            self._cookies_acquired_at = time.time()
            return True

        logger.warning("_acquire_cookies: ALL FAILED")
        return False

    async def crawl(self, url: str) -> dict[str, Any]:
        """Crawl a Boss Zhipin job search via curl_cffi + persistent cookies."""
        try:
            session = self._get_session()

            for attempt in range(2):
                if not await self._ensure_cookies():
                    return {
                        "success": False,
                        "error": (
                            "No valid cookies. Please open "
                            "https://www.zhipin.com in your browser, "
                            "complete captcha if shown, then retry."
                        ),
                    }

                ck = session.cookies.get_dict()
                logger.warning("crawl: pre-search cookies=%s", list(ck.keys()))

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

                    page_ok = False
                    for page_retry in range(2):
                        resp = session.get(
                            api_url,
                            impersonate="chrome124",
                            headers={"Referer": url},
                        )

                        if resp.status_code != 200:
                            logger.warning("API HTTP %d on page %d", resp.status_code, page_num)
                            break

                        data = resp.json()
                        code = data.get("code")
                        if code == 0 and "异常" not in resp.text:
                            page_jobs = data.get("zpData", {}).get("jobList", [])
                            if page_jobs:
                                all_jobs.extend(page_jobs)
                                pages_fetched = page_num
                            page_ok = True
                            break

                        if page_retry == 0 and code in (36, 37):
                            logger.warning("crawl page=%d code=%s, quick-refresh", page_num, code)
                            fresh = await self._quick_refresh_cookies()
                            if fresh and fresh.get("__zp_stoken__"):
                                for k, v in fresh.items():
                                    session.cookies.set(k, v, domain=".zhipin.com", path="/")
                                continue
                        break

                    if not page_ok:
                        if page_num == 1 and not all_jobs and attempt == 0:
                            continue  # 重试整个 crawl
                        break

                    if not data.get("zpData", {}).get("hasMore"):
                        break

                    await asyncio.sleep(random.uniform(3.0, 6.0))

                if all_jobs:
                    transformed = self._transform_jobs(all_jobs)
                    logger.warning("curl_cffi: %d jobs from %d page(s)",
                               len(transformed), pages_fetched)
                    ck = session.cookies.get_dict()
                    logger.warning("crawl: post-search cookies=%s", list(ck.keys()))
                    self._save_cookies(session)
                    return {"success": True, "jobs": transformed, "count": len(transformed)}

            return {"success": False, "error": "No job data from search API"}

        except Exception as e:
            logger.exception("Boss crawl failed")
            return {"success": False, "error": str(e)}

    async def crawl_detail(self, security_id: str) -> dict[str, Any]:
        """Crawl a Boss Zhipin job detail page.

        优先用 session 已有 cookie（来自搜索 API Set-Cookie 链）。
        code=37/36 时 quick-refresh 后重试一次。
        """
        try:
            session = self._get_session()

            for attempt in range(2):
                ck = session.cookies.get_dict()
                stoken = ck.get("__zp_stoken__", "<missing>")
                logger.warning("detail attempt=%d sid=%s stoken=%s",
                           attempt, security_id[:8],
                           stoken[:24] if len(stoken) > 24 else stoken)

                api_url = f"{BASE_URL}{DETAIL_API_PATH}?securityId={security_id}"
                resp = session.get(
                    api_url,
                    impersonate="chrome124",
                    headers={"Referer": f"{BASE_URL}/"},
                )

                if resp.status_code != 200:
                    return {"success": False, "error": f"HTTP {resp.status_code}"}

                data = resp.json()
                code = data.get("code")

                if code == 0:
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

                if attempt == 0 and code in (36, 37):
                    logger.warning(
                        "Detail API code=%s for securityId=%s, retrying with quick-refresh",
                        code, security_id[:8],
                    )
                    fresh = await self._quick_refresh_cookies()
                    new_stoken = fresh.get("__zp_stoken__") if fresh else None
                    if new_stoken:
                        session.cookies.set("__zp_stoken__", new_stoken,
                                           domain=".zhipin.com", path="/")
                        for k, v in fresh.items():
                            if k != "__zp_stoken__":
                                session.cookies.set(k, v, domain=".zhipin.com", path="/")
                        actual = session.cookies.get_dict().get("__zp_stoken__", "")
                        logger.warning("detail retry: new=%s session=%s",
                                   new_stoken[:24],
                                   actual[:24] if actual else "<missing>")
                    else:
                        logger.warning("quick-refresh returned no __zp_stoken__")
                    continue

                logger.warning("Detail API code=%s for securityId=%s", code, security_id[:8])
                return {
                    "success": False,
                    "error": (
                        f"API code={code}"
                        if code not in (36, 37)
                        else (
                            "Cookie expired and refresh failed. Please open "
                            "https://www.zhipin.com in your browser, "
                            "complete captcha if shown, then retry."
                        )
                    ),
                }

        except Exception as e:
            logger.exception("Boss detail crawl failed")
            return {"success": False, "error": str(e)}

    # ── Data transformation ────────────────────────────────────────────

    def _transform_jobs(self, raw_jobs: list[dict]) -> list[dict]:
        transformed = []
        for job in raw_jobs:
            # securityId 用于 API 调用(detail)，encryptJobId 用于拼详情页 URL
            job_id = job.get("securityId") or ""
            encrypt_job_id = job.get("encryptJobId") or ""

            transformed.append({
                "job_id": job_id,
                "title": job.get("jobName", ""),
                "company": job.get("brandName", ""),
                "company_id": job.get("encryptBrandId", ""),
                "salary": job.get("salaryDesc", ""),
                "location": job.get("cityName", "") or job.get("areaDistrict", ""),
                "experience": job.get("jobExperience", ""),
                "education": job.get("jobDegree", ""),
                "url": f"https://www.zhipin.com/job_detail/{encrypt_job_id}.html" if encrypt_job_id else "",
            })
        return transformed
