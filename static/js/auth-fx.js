/* D-OS Auth — One-time stat counter only */
(function () {
  "use strict";

  function initCounters() {
    document.querySelectorAll("[data-count-to]").forEach(function (el) {
      var target = parseInt(el.dataset.countTo, 10);
      var prefix = el.dataset.prefix || "";
      var suffix = el.dataset.suffix || "";
      var indicator = el.querySelector(".stat-card-indicator");
      var indicatorHTML = indicator ? " " + indicator.outerHTML : "";
      var duration = 700;
      var start = performance.now();

      function step(now) {
        var t = Math.min((now - start) / duration, 1);
        var eased = 1 - (1 - t) * (1 - t);
        var current = Math.round(eased * target);
        el.innerHTML = prefix + current.toLocaleString("en-IN") + suffix + indicatorHTML;
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }

  if (document.readyState !== "loading") initCounters();
  else document.addEventListener("DOMContentLoaded", initCounters);
})();
