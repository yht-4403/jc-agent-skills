/* jc-code.js — 把 <script type="text/plain" class="src"> 渲染成带行号、高亮、可复制的代码块
 *
 * 用法：把代码放在
 *   <div class="code-slot"><script type="text/plain" class="src"
 *        data-lang="python" data-title="这段在做什么">…代码…</script></div>
 * 然后引入本文件即可。样式在 style-core.css 的「代码块」一节。
 */
(function () {
  "use strict";

  var KW = {
    python: "def return if else elif for while in not and or import from as class with try except lambda None True False print self yield break continue is pass raise assert global del async await".split(" "),
    java: "public private protected class static void int double long float boolean if else for while return new final import package try catch throws this null true false String Map List HashMap switch case break continue extends implements interface volatile synchronized assert final".split(" "),
    sql: "select from where group by order having join left right inner on as and or not null insert update delete create table".split(" ")
  };

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function hl(line, kw) {
    var re = /(#[^\n]*|\/\/[^\n]*)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)/g;
    var out = "", last = 0, m;
    while ((m = re.exec(line)) !== null) {
      out += esc(line.slice(last, m.index));
      if (m[1]) out += '<span class="tok-c">' + esc(m[1]) + '</span>';
      else if (m[2]) out += '<span class="tok-s">' + esc(m[2]) + '</span>';
      else if (m[3]) out += '<span class="tok-n">' + esc(m[3]) + '</span>';
      else {
        var w = m[4];
        if (kw.indexOf(w) > -1) out += '<span class="tok-k">' + esc(w) + '</span>';
        else if (/^[A-Z][A-Za-z0-9]*$/.test(w)) out += '<span class="tok-t">' + esc(w) + '</span>';
        else out += esc(w);
      }
      last = m.index + m[0].length;
    }
    out += esc(line.slice(last));
    return out.length ? out : "&nbsp;";
  }

  function copyText(text, btn) {
    var done = function () {
      btn.textContent = "已复制";
      setTimeout(function () { btn.textContent = "复制"; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {});
    } else {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); done(); } catch (e) {}
      document.body.removeChild(ta);
    }
  }

  function render(s) {
    if (s.getAttribute("data-jc-code-done")) return;
    s.setAttribute("data-jc-code-done", "1");

    var lang = s.getAttribute("data-lang") || "python";
    var kw = KW[lang] || KW.python;
    var title = s.getAttribute("data-title") || "";
    var raw = s.textContent.replace(/\t/g, "    ").replace(/^\n+/, "").replace(/\s+$/, "");

    var body = raw.split("\n").map(function (l) {
      return '<span class="row">' + hl(l, kw) + '</span>';
    }).join("");

    var wrap = document.createElement("div");
    wrap.className = "code";
    wrap.innerHTML =
      '<div class="code-bar">' +
        '<span class="lang">' + lang + '</span>' +
        '<span class="ttl">' + title + '</span>' +
        '<button class="copy" type="button" style="margin-left:auto;background:transparent;border:1px solid #3A475A;color:#9FB0C4;font-size:10.5px;padding:2px 9px;border-radius:5px;cursor:pointer">复制</button>' +
      '</div>' +
      '<pre><code>' + body + '</code></pre>';

    s.parentNode.appendChild(wrap);
    wrap.querySelector(".copy").addEventListener("click", function () {
      copyText(raw, this);
    });
  }

  function boot() {
    [].slice.call(document.querySelectorAll('script.src[type="text/plain"]')).forEach(render);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
