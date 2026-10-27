/* jc-note.js — 页面标注：划线 + 备注
 *
 * 用法（两条即可）：
 *   <link rel="stylesheet" href="./assets/jc-note.css">
 *   <script src="./assets/jc-note.js" data-jc-note
 *           data-doc-id="gbdt-05" data-doc-title="第 05 讲 · GBDT 原理"></script>
 *
 * 数据存在 localStorage：jc-note:<doc-id>
 * 只有一种标记：不懂。一条标记可以跨多个段落，每段一个 mark，共享 data-jc-id。
 */
(function () {
  "use strict";

  var SELF = document.querySelector('script[data-jc-note]');
  if (!SELF) return;

  var DOC_ID = SELF.getAttribute('data-doc-id') || location.pathname;
  var DOC_TITLE = SELF.getAttribute('data-doc-title') || document.title;
  var STORE = 'jc-note:' + DOC_ID;

  var marks = [];
  var pendingRange = null;
  var composerId = null;
  var ui = {};

  /* ---------------- 工具 ---------------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
  }
  function save() {
    try { localStorage.setItem(STORE, JSON.stringify(marks)); } catch (e) {}
  }
  function load() {
    try {
      var raw = localStorage.getItem(STORE);
      marks = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(marks)) marks = [];
    } catch (e) { marks = []; }
    marks = marks.filter(function (m) { return m && m.text; });
  }

  function toast(msg) {
    if (!ui.toast) return;
    ui.toast.textContent = msg;
    ui.toast.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { ui.toast.classList.remove('show'); }, 2400);
  }

  /* ---------------- 文本定位 ---------------- */
  function collectText(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = n.parentElement;
        if (!p) return NodeFilter.FILTER_REJECT;
        if (p.closest('.jcn-drawer,.jcn-tool,.jcn-fab,.jcn-toast,script,style,svg')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var out = [], n;
    while ((n = walker.nextNode())) out.push(n);
    return out;
  }

  /* 选中文本里的空白（段落之间的换行、缩进）在纯文本拼接里不存在。
     所以匹配时不要求空白完全一致：needle 的空白段对应 hay 的任意空白。 */
  function escRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  function buildRe(needle) {
    var parts = String(needle).split(/\s+/).filter(function (x) { return x.length; });
    if (!parts.length) return null;
    return new RegExp(parts.map(escRe).join('\\s*'), 'g');
  }
  function looseCount(hay, needle) {
    var re = buildRe(needle);
    if (!re) return 0;
    var n = 0, m;
    while ((m = re.exec(hay))) {
      n++;
      re.lastIndex = m.index + 1;
      if (!m[0].length) re.lastIndex++;
    }
    return n;
  }

  function findRange(root, text, occ) {
    var nodes = collectText(root);
    var full = '', spans = [], i;
    for (i = 0; i < nodes.length; i++) {
      spans.push([full.length, full.length + nodes[i].nodeValue.length]);
      full += nodes[i].nodeValue;
    }

    var re = buildRe(text);
    if (!re) return null;
    var m, n = 0, hit = null;
    while ((m = re.exec(full))) {
      if (n === occ) { hit = m; break; }
      n++;
      re.lastIndex = m.index + 1;
      if (!m[0].length) re.lastIndex++;
    }
    if (!hit) return null;

    var idx = hit.index, end = hit.index + hit[0].length;
    var startNode = null, startOff = 0, endNode = null, endOff = 0;
    for (i = 0; i < spans.length; i++) {
      if (!startNode && idx >= spans[i][0] && idx < spans[i][1]) {
        startNode = nodes[i];
        startOff = Math.min(Math.max(idx - spans[i][0], 0), nodes[i].nodeValue.length);
      }
      if (startNode && end <= spans[i][1]) {
        endNode = nodes[i];
        endOff = Math.min(Math.max(end - spans[i][0], 0), nodes[i].nodeValue.length);
        break;
      }
    }
    if (!startNode || !endNode) return null;
    try {
      var r = document.createRange();
      r.setStart(startNode, startOff);
      r.setEnd(endNode, endOff);
      return r;
    } catch (e) { return null; }
  }

  function sectionOf(node) {
    var el = node.nodeType === 1 ? node : node.parentElement;
    if (!el) return null;
    return el.closest('section[id]') || el.closest('main') || document.body;
  }
  function sectionTitle(sec) {
    if (!sec) return '';
    var h = sec.querySelector('h2');
    return h ? h.textContent.trim() : (sec.getAttribute('data-title') || '');
  }

  /* ---------------- 划线：按文本节点拆分，支持跨段 ---------------- */
  function textNodesInRange(range) {
    var root = range.commonAncestorContainer;
    var out = [], n;
    if (root.nodeType === 3) {
      return root.nodeValue && root.nodeValue.trim() ? [root] : [];
    }
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (t) {
        if (!t.nodeValue || !t.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = t.parentElement;
        if (!p) return NodeFilter.FILTER_REJECT;
        if (p.closest('.jcn-drawer,.jcn-tool,.jcn-fab,.jcn-toast,script,style,svg')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    while ((n = walker.nextNode())) {
      if (!nodeInRange(range, n)) continue;
      out.push(n);
    }
    return out;
  }

  function nodeInRange(range, node) {
    try {
      var r = document.createRange();
      r.selectNodeContents(node);
      return range.compareBoundaryPoints(Range.END_TO_START, r) < 0 &&
             range.compareBoundaryPoints(Range.START_TO_END, r) > 0;
    } catch (e) { return false; }
  }

  function wrapRange(range, id) {
    var nodes = textNodesInRange(range);
    if (!nodes.length) return 0;

    /* 先把每段的起止算好，再动 DOM，避免偏移被前一次切割影响 */
    var subs = [];
    nodes.forEach(function (n) {
      var s = (n === range.startContainer) ? range.startOffset : 0;
      var e = (n === range.endContainer) ? range.endOffset : n.nodeValue.length;
      if (e > s) subs.push([n, s, e]);
    });
    if (!subs.length) return 0;

    var ok = 0;
    /* 从后往前插，前面的文本节点偏移不受影响 */
    for (var i = subs.length - 1; i >= 0; i--) {
      try {
        var r = document.createRange();
        r.setStart(subs[i][0], subs[i][1]);
        r.setEnd(subs[i][0], subs[i][2]);
        var mark = document.createElement('mark');
        mark.className = 'jcn-mark';
        mark.setAttribute('data-jc-id', id);
        mark.appendChild(r.extractContents());
        r.insertNode(mark);
        ok++;
      } catch (e) {}
    }
    return ok;
  }

  function partsOf(id) {
    return [].slice.call(document.querySelectorAll('mark.jcn-mark[data-jc-id="' + id + '"]'));
  }

  function unwrap(el) {
    if (!el || !el.parentNode) return;
    var p = el.parentNode;
    while (el.firstChild) p.insertBefore(el.firstChild, el);
    p.removeChild(el);
    p.normalize();
  }

  /* ---------------- 选中 → 工具栏 ---------------- */
  function onSelection() {
    if (ui.drawer.contains(document.activeElement)) return;
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed) { hideTool(); return; }
    var range = sel.getRangeAt(0);
    if (!range.toString().trim()) { hideTool(); return; }
    var main = document.querySelector('main');
    if (!main || !main.contains(range.commonAncestorContainer)) { hideTool(); return; }

    /* 选区里不能已经有标记 */
    var nodes = textNodesInRange(range);
    for (var i = 0; i < nodes.length; i++) {
      var p = nodes[i].parentElement;
      if (p && p.closest('mark.jcn-mark')) { hideTool(); return; }
    }

    closeComposer();
    pendingRange = range.cloneRange();
    showTool(range);
  }

  function showTool(range) {
    var t = ui.tool;
    var rects = range.getClientRects();
    var rect = rects.length ? rects[rects.length - 1] : range.getBoundingClientRect();
    t.classList.add('show');
    var tw = t.offsetWidth, th = t.offsetHeight;
    var left = rect.left + rect.width / 2 - tw / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
    var top = rect.top - th - 9;
    if (top < 8) top = rect.bottom + 9;
    t.style.left = left + 'px';
    t.style.top = top + 'px';
  }
  function hideTool() {
    if (ui.tool) ui.tool.classList.remove('show');
  }

  function lastRect(range) {
    var rects = range.getClientRects();
    return rects.length ? rects[rects.length - 1] : range.getBoundingClientRect();
  }

  /* ---------------- 就地评论框 ---------------- */
  function showComposer(id, rect) {
    if (!ui.composer) return;
    var m = marks.filter(function (x) { return x.id === id; })[0];
    composerId = id;
    ui.cin.value = (m && m.note) || '';
    ui.composer.classList.add('show');

    var w = ui.composer.offsetWidth, h = ui.composer.offsetHeight;
    var left = rect ? rect.left : (window.innerWidth - w) / 2;
    var top = rect ? rect.top - h - 12 : window.innerHeight / 2;
    left = Math.max(10, Math.min(left, window.innerWidth - w - 10));
    if (top < 10) top = (rect ? rect.bottom + 12 : 10);
    ui.composer.style.left = left + 'px';
    ui.composer.style.top = top + 'px';

    try { ui.cin.focus({ preventScroll: true }); } catch (e) { ui.cin.focus(); }
    var n = ui.cin.value.length;
    try { ui.cin.setSelectionRange(n, n); } catch (e) {}
  }

  function closeComposer() {
    if (!ui.composer || !ui.composer.classList.contains('show')) return;
    var v = ui.cin.value;
    if (composerId) {
      setNote(composerId, v);
      var ta = ui.body.querySelector('[data-note="' + composerId + '"]');
      if (ta) { ta.value = v; grow(ta); }
    }
    ui.composer.classList.remove('show');
    composerId = null;
  }

  function takePending() {
    var r = pendingRange;
    pendingRange = null;
    hideTool();
    var sel = window.getSelection();
    if (sel) sel.removeAllRanges();
    return r;
  }

  /* ---------------- 新增 / 删除 ---------------- */
  function addMark(note, range) {
    range = range || takePending();
    if (!range) { toast('先选中一段文字'); return null; }

    var text = range.toString();
    if (!text.trim()) return null;

    var sec = sectionOf(range.startContainer);
    var before = document.createRange();
    before.selectNodeContents(sec);
    try { before.setEnd(range.startContainer, range.startOffset); } catch (e) { return null; }
    var pre = before.toString();
    var occ = looseCount(pre, text);

    var m = {
      id: uid(),
      text: text,
      note: note || '',
      section: sec && sec.id ? sec.id : '',
      sectionTitle: sectionTitle(sec),
      occ: occ,
      ts: Date.now()
    };
    if (!wrapRange(range, m.id)) { toast('这段没法标记，换个位置试试'); return null; }
    marks.push(m);
    save();
    render();
    return m;
  }

  function deleteMark(id) {
    partsOf(id).forEach(unwrap);
    marks = marks.filter(function (m) { return m.id !== id; });
    save(); render();
  }

  function clearAll() {
    marks.forEach(function (m) { partsOf(m.id).forEach(unwrap); });
    marks = [];
    save(); render();
    toast('已清空');
  }

  function setNote(id, note) {
    var m = marks.filter(function (x) { return x.id === id; })[0];
    if (!m) return;
    m.note = note;
    save();
  }

  /* ---------------- 定位 / 闪烁 ---------------- */
  function focusMark(id) {
    openDrawer();
    var parts = partsOf(id);
    if (!parts.length) return;
    parts[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    parts.forEach(function (el) {
      el.classList.remove('jcn-flash');
      void el.offsetWidth;
      el.classList.add('jcn-flash');
    });
    var item = ui.body.querySelector('[data-item="' + id + '"]');
    if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /* ---------------- 渲染 ---------------- */
  function render() {
    ui.cnt.textContent = marks.length;
    ui.cnt.classList.toggle('zero', marks.length === 0);
    ui.badge.textContent = marks.length;

    if (!marks.length) {
      ui.body.innerHTML = '<div class="jcn-empty"><b>还没有标记</b>选中正文里看不懂的词或句子，点「不懂」。<br>可以连着几行一起选；标完能补一句备注。标记只存在本机。</div>';
      return;
    }
    var html = marks.slice().sort(function (a, b) { return b.ts - a.ts; }).map(function (m) {
      return '<div class="jcn-item" data-item="' + m.id + '">' +
        '<div class="jcn-meta">' +
          '<span class="jcn-tag">不懂</span>' +
          '<span class="jcn-src" title="' + esc(m.sectionTitle) + '">' + esc(m.sectionTitle || '页面') + '</span>' +
        '</div>' +
        '<div class="jcn-txt">' + esc(m.text.replace(/\s+/g, ' ').trim()) + '</div>' +
        '<textarea class="jcn-notein" data-note="' + m.id + '" rows="1" placeholder="加个备注（可选）">' + esc(m.note) + '</textarea>' +
        '<div class="jcn-ops">' +
          '<button type="button" data-act="goto" data-id="' + m.id + '">定位</button>' +
          '<button type="button" data-act="del" data-id="' + m.id + '" class="del">删除</button>' +
        '</div>' +
      '</div>';
    }).join('');
    ui.body.innerHTML = html;
    growAll();
  }

  function grow(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }
  function growAll() {
    [].slice.call(ui.body.querySelectorAll('.jcn-notein')).forEach(grow);
  }

  /* ---------------- 抽屉 ---------------- */
  function openDrawer() {
    ui.drawer.classList.add('open');
    document.body.classList.add('jcn-open');
    ui.fab.setAttribute('aria-expanded', 'true');
  }
  function closeDrawer() {
    ui.drawer.classList.remove('open');
    document.body.classList.remove('jcn-open');
    ui.fab.setAttribute('aria-expanded', 'false');
  }

  /* ---------------- 导出 / 复制 ---------------- */
  function toMarkdown() {
    var d = new Date();
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    var stamp = d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
    var out = ['# 看不懂清单 · ' + DOC_TITLE, '', '> 导出时间：' + stamp + '　共 ' + marks.length + ' 条', ''];
    marks.slice().sort(function (a, b) { return a.ts - b.ts; }).forEach(function (m, i) {
      out.push('## ' + (i + 1) + '. [不懂] ' + (m.sectionTitle || '页面'));
      out.push('');
      out.push('> ' + m.text.replace(/\s+/g, ' ').trim());
      if (m.note) { out.push(''); out.push('我的备注：' + m.note); }
      out.push('');
    });
    out.push('---');
    out.push('请按这份清单，只拓展对应段落，不要重写整页。');
    return out.join('\n');
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(function () { fallbackCopy(text); });
    }
    fallbackCopy(text);
    return Promise.resolve();
  }
  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  function download() {
    var blob = new Blob([toMarkdown()], { type: 'text/markdown;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = DOC_ID + '-看不懂清单.md';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 600);
  }

  /* ---------------- 构建 UI ---------------- */
  function build() {
    var fab = document.createElement('button');
    fab.className = 'jcn-fab';
    fab.type = 'button';
    fab.setAttribute('aria-expanded', 'false');
    fab.innerHTML = '<span class="jcn-ico">✎</span><span>标注</span><span class="jcn-cnt zero">0</span>';

    var tool = document.createElement('div');
    tool.className = 'jcn-tool';
    tool.innerHTML = '<button type="button" data-act="q">不懂</button>';

    var drawer = document.createElement('aside');
    drawer.className = 'jcn-drawer';
    drawer.setAttribute('aria-label', '标注面板');
    drawer.innerHTML =
      '<div class="jcn-head"><b>看不懂清单</b><span class="jcn-badge">0</span>' +
        '<button class="jcn-x" type="button" aria-label="关闭">×</button></div>' +
      '<div class="jcn-body"></div>' +
      '<div class="jcn-foot">' +
        '<div class="jcn-row">' +
          '<button class="jcn-btn primary" type="button" data-act="copy">复制清单</button>' +
          '<button class="jcn-btn" type="button" data-act="md">下载 .md</button>' +
          '<button class="jcn-btn" type="button" data-act="clear">清空</button>' +
        '</div>' +
        '<p class="jcn-hint">标记只存在这台电脑的浏览器里，不上传。换浏览器或清缓存会丢。</p>' +
      '</div>';

    var composer = document.createElement('div');
    composer.className = 'jcn-composer';
    composer.innerHTML =
      '<input class="jcn-cin" type="text" placeholder="补充一句（可选）" autocomplete="off">' +
      '<button class="jcn-cok" type="button" aria-label="保存">' +
        '<svg viewBox="0 0 24 24"><path d="M4 12l6 6L20 6"/></svg>' +
      '</button>';

    var t = document.createElement('div');
    t.className = 'jcn-toast';

    document.body.appendChild(fab);
    document.body.appendChild(tool);
    document.body.appendChild(composer);
    document.body.appendChild(drawer);
    document.body.appendChild(t);

    ui = {
      fab: fab, tool: tool, drawer: drawer, toast: t,
      cnt: fab.querySelector('.jcn-cnt'),
      badge: drawer.querySelector('.jcn-badge'),
      body: drawer.querySelector('.jcn-body'),
      composer: composer,
      cin: composer.querySelector('.jcn-cin')
    };

    /* 事件 */
    fab.addEventListener('click', function () {
      drawer.classList.contains('open') ? closeDrawer() : openDrawer();
    });
    drawer.querySelector('.jcn-x').addEventListener('click', closeDrawer);

    tool.addEventListener('mousedown', function (e) { e.preventDefault(); });
    tool.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      if (btn.getAttribute('data-act') === 'q') {
        var rect = pendingRange ? lastRect(pendingRange) : null;
        var m = addMark('');
        if (m) showComposer(m.id, rect);
      }
    });

    /* 评论框 */
    var cTimer = null;
    composer.querySelector('.jcn-cok').addEventListener('click', closeComposer);
    composer.querySelector('.jcn-cin').addEventListener('input', function () {
      if (composerId === null) return;
      var id = composerId, v = ui.cin.value;
      var ta = ui.body.querySelector('[data-note="' + id + '"]');
      if (ta) { ta.value = v; grow(ta); }
      clearTimeout(cTimer);
      cTimer = setTimeout(function () { setNote(id, v); }, 400);
    });

    /* 备注：输入即存，防抖 */
    var noteTimer = null;
    drawer.addEventListener('input', function (e) {
      var ta = e.target.closest('.jcn-notein');
      if (!ta) return;
      grow(ta);
      var id = ta.getAttribute('data-note');
      clearTimeout(noteTimer);
      noteTimer = setTimeout(function () { setNote(id, ta.value); }, 500);
    });
    drawer.addEventListener('blur', function (e) {
      var ta = e.target.closest && e.target.closest('.jcn-notein');
      if (!ta) return;
      clearTimeout(noteTimer);
      setNote(ta.getAttribute('data-note'), ta.value);
    }, true);

    drawer.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      var act = b.getAttribute('data-act');
      var id = b.getAttribute('data-id');
      if (act === 'goto') focusMark(id);
      else if (act === 'del') deleteMark(id);
      else if (act === 'copy') { copyText(toMarkdown()).then(function () { toast('已复制，粘回对话即可'); }); }
      else if (act === 'md') download();
      else if (act === 'clear') { if (confirm('清空全部标记？')) clearAll(); }
    });

    function inUI(t) {
      return !!(t && t.closest && t.closest('.jcn-tool,.jcn-drawer,.jcn-fab,.jcn-composer'));
    }
    document.addEventListener('mouseup', function (e) {
      if (inUI(e.target)) return;
      setTimeout(onSelection, 10);
    });
    document.addEventListener('touchend', function (e) {
      if (inUI(e.target)) return;
      setTimeout(onSelection, 220);
    });
    document.addEventListener('mousedown', function (e) {
      if (!inUI(e.target)) { hideTool(); closeComposer(); }
    });
    document.addEventListener('keydown', function (e) {
      var inComposer = composerId && document.activeElement === ui.cin;
      if (e.key === 'Enter' && inComposer) { e.preventDefault(); closeComposer(); return; }
      if (e.key === 'Escape') {
        if (composerId) { closeComposer(); return; }
        hideTool(); closeDrawer();
      }
    });
    document.addEventListener('click', function (e) {
      var mk = e.target && e.target.closest ? e.target.closest('mark.jcn-mark') : null;
      if (mk) focusMark(mk.getAttribute('data-jc-id'));
    });
    window.addEventListener('scroll', hideTool, { passive: true });
    window.addEventListener('resize', hideTool, { passive: true });
  }

  /* ---------------- 恢复已有标记 ---------------- */
  function restore() {
    marks.forEach(function (m) {
      if (partsOf(m.id).length) return;
      var root = m.section ? (document.getElementById(m.section) || document.querySelector('main')) : document.querySelector('main');
      if (!root) return;
      var r = findRange(root, m.text, m.occ || 0);
      if (r) wrapRange(r, m.id);
    });
  }

  /* ---------------- 启动 ---------------- */
  function boot() {
    /* 旧版本留过 AI 配置，这里顺手清掉 */
    try { localStorage.removeItem('jc-note-ai'); } catch (e) {}
    load();
    build();
    restore();
    render();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  /* 给外部（自动注入 / 测试）留的接口 */
  window.JCNote = {
    open: openDrawer,
    close: closeDrawer,
    marks: function () { return marks.slice(); },
    markdown: toMarkdown,
    add: function (range, _type, note) { return addMark(note || '', range); },
    clear: clearAll,
    version: '2.0.0'
  };
})();
