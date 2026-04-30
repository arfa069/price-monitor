# Unified Cron Settings Card — Design Spec

**Date:** 2026-04-30  
**Status:** Approved

## Motivation

Product crawl cron and job crawl cron are currently scattered across three locations:

| Location | What it holds |
|----------|---------------|
| `ScheduleConfigPage.tsx` | Product crawl cron (embedded inside interval/cron toggle card) |
| `ProductCrawlSettings.tsx` | Duplicate product crawl cron editor on ProductsPage |
| `CronSettings.tsx` | Job crawl cron editor on JobsPage |

No single place shows both timer configurations. The `/scheduler/status` endpoint was recently extended to return both jobs' runtime status but is not consumed by the frontend. This spec unifies all cron configuration into one card on `ScheduleConfigPage`.

## Design

### Page Structure (ScheduleConfigPage)

Three cards in vertical order:

```
┌─ 抓取频率配置 ─────────────────────────────────┐
│  调度模式: [间隔模式] [Cron 模式]                │
│  (间隔模式) 每 [__] 小时执行  [保存]             │
│  (Cron 模式) "Cron 表达式请在下方「Cron 定时配置」卡片中编辑"  │
└────────────────────────────────────────────────┘

┌─ Cron 定时配置 ────────────────────────────────┐
│                                                  │
│  商品爬取                                       │
│  Cron: [____________]  时区: [_________]         │
│  下次执行: 2026-04-30 14:00 CST  (或 "未注册")    │
│  [保存]                                          │
│                                                  │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                                  │
│  职位爬取                                       │
│  Cron: [____________]                            │
│  下次执行: 2026-05-01 09:00 CST  (或 "未注册")    │
│  [保存]                                          │
│                                                  │
└──────────────────────────────────────────────────┘

┌─ 数据保留与其他配置 ───────────────────────────┐
│  (existing content unchanged)                   │
└────────────────────────────────────────────────┘
```

### Data Flow

```
Page mount
  ├─ GET /config              → crawl_cron, crawl_timezone, job_crawl_cron
  └─ GET /scheduler/status    → jobs.product_crawl.next_run_at,
                                  jobs.job_crawl.next_run_at

Product save → PATCH /config { crawl_cron, crawl_timezone }
Job save     → PUT /config/job-crawl-cron { job_crawl_cron }

After either save → re-fetch both /config and /scheduler/status
```

### Key Design Decisions

1. **No draft persistence.** Removed localStorage draft save. The form always reflects the current backend value.
2. **Timezone only for product crawl.** Job crawl reuses `crawl_timezone` from user config for APScheduler registration (existing backend behavior). The schedule status display shows the shared timezone.
3. **Independent save buttons.** Product and job each have their own save button. Saving one does not touch the other.
4. **Job cron can be empty.** When `job_crawl_cron` is null, the backend uses the default `0 9 * * *`. The input placeholder shows this default.
5. **Next run time from scheduler.** Displayed read-only below each cron input. "未注册" when the APScheduler job is not found (e.g., scheduler not started, or no cron configured).

### File Changes

| Action | File | Notes |
|--------|------|-------|
| Refactor | `frontend/src/pages/ScheduleConfigPage.tsx` | Restructure into 3 cards; extract cron editing from interval/cron card into new unified card; remove draft logic |
| Add API | `frontend/src/api/config.ts` | New `getSchedulerStatus()` function calling `GET /scheduler/status` |
| Delete | `frontend/src/components/ProductCrawlSettings.tsx` | Superseded by unified card |
| Delete | `frontend/src/components/CronSettings.tsx` | Superseded by unified card |
| Cleanup | `frontend/src/pages/ProductsPage.tsx` | Remove `ProductCrawlSettings` import and usage |
| Cleanup | `frontend/src/pages/JobsPage.tsx` | Remove `CronSettings` import and usage |

### Backend Dependency

`GET /scheduler/status` was extended in this session to return:

```json
{
  "scheduler": "running",
  "timezone": "Asia/Shanghai",
  "jobs": {
    "product_crawl": {
      "registered": true,
      "cron_expression": "0 */2 * * *",
      "next_run_at": "2026-04-30T10:00:00+08:00"
    },
    "job_crawl": {
      "registered": true,
      "cron_expression": "0 9 * * *",
      "next_run_at": "2026-05-01T09:00:00+08:00"
    }
  }
}
```

This is already deployed. No further backend changes needed.

### States & Edge Cases

| State | Handling |
|-------|----------|
| Scheduler not started | `GET /scheduler/status` returns 503 → show "调度器未启动" for both next-run displays |
| Scheduler running, job not registered | `registered: false` → show "未注册" for that job's next-run |
| cron input invalid format | Validate client-side before submit (5 segments). Show inline error. |
| API call fails | Show error message via `message.error()`. Keep current values in inputs. |
| `job_crawl_cron` is null | Input shows placeholder "0 9 * * *" (default). Backend treats null as default. |

### What Is NOT Changing

- Backend endpoints and behavior
- Product interval mode (`crawl_frequency_hours`) logic
- Data retention settings card
- Product/Job crawl triggering and results display
