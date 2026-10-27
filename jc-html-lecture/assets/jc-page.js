/* jc-page.js — 页面外壳的通用交互：滚动进度、目录高亮、节数显示、回到顶部。
 * 骨架里的 id 固定：pgBar / tbMeta / toc / toTop。
 * 元素缺失时静默跳过，不影响页面其它功能。
 */
(function () {
  "use strict";

  function boot() {
    var bar = document.getElementById("pgBar");
    var meta = document.getElementById("tbMeta");
    var toTop = document.getElementById("toTop");
    var secs = [].slice.call(document.querySelectorAll("section.chapter"));
    var links = [].slice.call(document.querySelectorAll("#toc a"));
    if (!secs.length && !bar) return;

    function sync() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      if (bar) bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0).toFixed(1) + "%";
      if (toTop) toTop.classList.toggle("show", h.scrollTop > 700);
      var idx = 0;
      for (var i = 0; i < secs.length; i++) {
        if (secs[i].getBoundingClientRect().top < 140) idx = i;
      }
      links.forEach(function (a, i) { a.classList.toggle("on", i === idx); });
      if (meta && secs.length) meta.textContent = (idx + 1) + " / " + secs.length + " 节";
    }

    window.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync, { passive: true });
    sync();

    if (toTop) {
      toTop.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
