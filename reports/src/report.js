// SPDX-License-Identifier: Apache-2.0
(function () {
  "use strict";

  // Collapsible parts in the table of contents.
  document.querySelectorAll(".toc .part > button").forEach(function (btn) {
    btn.setAttribute("aria-expanded", "true");
    btn.addEventListener("click", function () {
      var part = btn.parentElement;
      var collapsed = part.classList.toggle("collapsed");
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    });
  });

  // Drawer on narrow screens.
  var toggle = document.getElementById("toc-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      document.body.classList.toggle("toc-open");
    });
  }
  document.addEventListener("click", function (e) {
    if (!document.body.classList.contains("toc-open")) return;
    var side = document.querySelector(".side");
    if (
      e.target.closest(".toc a") ||
      (!side.contains(e.target) && e.target !== toggle)
    ) {
      document.body.classList.remove("toc-open");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") document.body.classList.remove("toc-open");
  });

  // Scrollspy: highlight the section whose heading most recently passed the top.
  var links = Array.prototype.slice.call(
    document.querySelectorAll(".toc a[href^='#']"),
  );
  var targets = links
    .map(function (a) {
      return document.getElementById(a.getAttribute("href").slice(1));
    })
    .filter(Boolean);
  function spy() {
    var y = window.scrollY + 120;
    var current = targets[0];
    for (var i = 0; i < targets.length; i++) {
      if (targets[i].offsetTop <= y) current = targets[i];
    }
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4)
      current = targets[targets.length - 1];
    links.forEach(function (a) {
      var on = current && a.getAttribute("href") === "#" + current.id;
      a.classList.toggle("active", on);
      if (on) a.setAttribute("aria-current", "location");
      else a.removeAttribute("aria-current");
    });
    var active = document.querySelector(".toc a.active");
    if (active) {
      var part = active.closest(".part");
      if (part && part.classList.contains("collapsed"))
        part.classList.remove("collapsed");
    }
  }
  var ticking = false;
  window.addEventListener(
    "scroll",
    function () {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(function () {
          spy();
          ticking = false;
        });
      }
    },
    { passive: true },
  );
  window.addEventListener("resize", spy);
  spy();

  // Copy buttons on command blocks.
  document.querySelectorAll("pre.cmd").forEach(function (pre) {
    var btn = document.createElement("button");
    btn.className = "copy";
    btn.type = "button";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var text =
        Array.prototype.map
          .call(pre.querySelectorAll(".line"), function (l) {
            return l.textContent;
          })
          .join("\n") || pre.innerText.replace(/^Copy$/m, "");
      var done = function () {
        btn.textContent = "Copied";
        setTimeout(function () {
          btn.textContent = "Copy";
        }, 1400);
      };
      try {
        navigator.clipboard.writeText(text).then(done, function () {
          select(pre);
        });
      } catch (err) {
        select(pre);
      }
    });
    pre.appendChild(btn);
  });
  function select(el) {
    var r = document.createRange();
    r.selectNodeContents(el);
    var s = window.getSelection();
    s.removeAllRanges();
    s.addRange(r);
  }
})();
