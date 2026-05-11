import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        console_logs = []
        page.on("console", lambda msg: console_logs.append("[%s] %s" % (msg.type, msg.text)))
        page.on("pageerror", lambda err: console_logs.append("[PAGE ERROR] %s" % err))
        print("=== Navigating to http://localhost:3001 ===")
        await page.goto("http://localhost:3001", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshot_before_login.png")
        if await page.locator("input[type='password']").count() > 0:
            print("=== Login page detected ===")
            inputs = await page.locator("input").all()
            print("Found %d inputs" % len(inputs))
            for i, inp in enumerate(inputs):
                t = await inp.get_attribute("type") or "text"
                ph = await inp.get_attribute("placeholder") or ""
                print("  Input %d: type=%s placeholder=%s" % (i, t, ph))
            await page.locator("input >> nth=0").fill("default123")
            await page.locator("input[type='password']").fill("123456")
            btn = page.locator("button:has-text('登录'), button:has-text('Login'), button[type='submit']").first
            if await btn.count() > 0:
                await btn.click()
            else:
                await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)
            await page.screenshot(path="screenshot_after_login.png")
        print("=== Looking for user menu trigger ===")
        selectors = ["[class*=user]", "[class*=avatar]", "[class*=profile]", ".ant-dropdown-trigger", "[class*=dropdown-trigger]"]
        trigger = None
        for sel in selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                box = await loc.bounding_box()
                if box and box["y"] < 200 and box["x"] > 800:
                    trigger = loc
                    print("Found trigger: %s" % sel)
                    break
        if trigger is None:
            print("No standard trigger found. Searching top-right...")
            all_els = await page.locator("body >> *").all()
            candidates = []
            for el in all_els:
                box = await el.bounding_box()
                text = await el.inner_text()
                if box and box["y"] < 150 and box["x"] > 900 and text and 0 < len(text.strip()) < 50:
                    cls = await el.get_attribute("class") or ""
                    tag = await el.evaluate("e => e.tagName.toLowerCase()")
                    candidates.append({"tag": tag, "class": cls, "text": text.strip(), "x": box["x"], "y": box["y"]})
            print("Candidates:")
            for c in candidates[:20]:
                print("  %s" % c)
            for c in candidates:
                if "用户" in c["text"] or "user" in c["text"].lower():
                    cls_sel = c["class"].strip().replace(" ", ".") if c["class"] else ""
                    if cls_sel:
                        trigger = page.locator("." + cls_sel).first
                    if trigger and await trigger.count() > 0:
                        print("Selected trigger: %s" % c)
                        break
        if trigger is None:
            print("ERROR: No trigger found!")
            h = page.locator("header, .ant-layout-header, [class*=header]").first
            if await h.count() > 0:
                print(await h.inner_html())
            await browser.close()
            return
        html = await trigger.evaluate("e => e.outerHTML")
        tag = await trigger.evaluate("e => e.tagName.toLowerCase()")
        cls = await trigger.get_attribute("class") or ""
        text = await trigger.inner_text()
        print("\n=== TRIGGER ELEMENT ===")
        print("Tag: %s" % tag)
        print("Classes: %s" % cls)
        print("Text: %s" % text)
        print("HTML: %s" % html[:500])
        parent = await trigger.evaluate("e => e.parentElement.outerHTML")
        print("\nParent HTML: %s" % parent[:800])
        print("\n=== CLICKING TRIGGER ===")
        await trigger.click()
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshot_after_click.png")
        print("Screenshot saved")
        print("\n=== CHECKING FOR DROPDOWN ===")
        ds = [".ant-dropdown", ".ant-dropdown-menu", "[class*=dropdown]", "[class*=overlay]", "[class*=popup]", ".ant-popover", "[role=menu]"]
        found = False
        for sel in ds:
            loc = page.locator(sel)
            cnt = await loc.count()
            if cnt > 0:
                for i in range(min(cnt, 3)):
                    el = loc.nth(i)
                    box = await el.bounding_box()
                    vis = await el.is_visible()
                    h = await el.evaluate("e => e.outerHTML")
                    print("Found %s #%d: visible=%s box=%s" % (sel, i, vis, box))
                    print("  HTML: %s" % h[:500])
                    found = True
        if not found:
            print("No dropdown elements found after click")
        print("\n=== FLOATING ELEMENTS ===")
        floats = await page.locator("body > div").all()
        print("body > div count: %d" % len(floats))
        for i, el in enumerate(floats):
            h = await el.evaluate("e => e.outerHTML")
            vis = await el.is_visible()
            print("  #%d visible=%s html=%s" % (i, vis, h[:200]))
        print("\n=== CONSOLE LOGS ===")
        for log in console_logs:
            print(log)
        await browser.close()

asyncio.run(main())
