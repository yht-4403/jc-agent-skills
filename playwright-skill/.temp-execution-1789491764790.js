const { chromium } = require("playwright");
const path = require("path");
const URL = "http://127.0.0.1:5173/";
const OUT = "/Users/JCProjects/ai-topup-ui-grok-2026-09-14/shots";

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");

  const title = await page.locator("h1").innerText();
  const sub = await page.locator(".hero .sub").innerText();
  const headerCta = await page.locator("header.top .btn").innerText();
  const nav = await page.locator("header.top nav").count();
  const notOfficial = await page.getByText("不是官方").count();
  const faqQ = await page.locator("#faq summary").first().innerText();
  const faqA = await page.locator("#faq details").first().locator("p").innerText();
  const qr = await page.locator(".dock img").getAttribute("src");
  console.log({ title, sub, headerCta, nav, notOfficial, faqQ, faqA: faqA.slice(0, 40), qr });

  await page.screenshot({ path: path.join(OUT, "react-desktop.png"), clip: { x: 0, y: 0, width: 1440, height: 900 } });

  await page.locator("#faq").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(OUT, "react-faq.png"), clip: { x: 0, y: 0, width: 1440, height: 900 } });

  await page.locator("#proof").scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.join(OUT, "react-proof.png"), clip: { x: 0, y: 0, width: 1440, height: 900 } });

  await page.locator(".proof-card").first().click();
  await page.waitForSelector(".zoom");
  const zoomOpen = await page.locator(".zoom").count();
  console.log("zoom", zoomOpen);
  await page.screenshot({ path: path.join(OUT, "react-zoom.png"), clip: { x: 0, y: 0, width: 1440, height: 900 } });
  await page.locator(".zoom-close").click();

  await page.locator("header.top .btn").click();
  await page.waitForSelector("#wechat", { state: "visible" });
  const wechatSrc = await page.locator("#wechat .qr").getAttribute("src");
  console.log("wechat qr", wechatSrc);
  await page.screenshot({ path: path.join(OUT, "react-wechat.png"), clip: { x: 0, y: 0, width: 1440, height: 900 } });
  await page.getByRole("button", { name: "关闭" }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(OUT, "react-mobile.png"), clip: { x: 0, y: 0, width: 390, height: 844 } });

  console.log("errors", errors);
  await browser.close();
})();
