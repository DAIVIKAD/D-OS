(function () {
  "use strict";

  const RETRO_PALETTE = [
    "#66FF99",
    "#ff5577",
    "#33ccff",
    "#ffe66d",
    "#ff4fd8",
    "#9b5cff",
    "#4faf70",
    "#ff9966",
    "#66ccff",
    "#ffcc00"
  ];

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function setDefaultDates() {
    const today = new Date().toISOString().slice(0, 10);
    document.querySelectorAll('input[type="date"][required]').forEach((input) => {
      if (!input.value) input.value = today;
    });
  }

  function parsePayload(canvas) {
    try {
      return JSON.parse(canvas.dataset.payload || "{}");
    } catch (error) {
      return { labels: [], values: [] };
    }
  }

  function normalizeDatasets(payload, chartType) {
    if (payload.datasets && Array.isArray(payload.datasets)) {
      return payload.datasets;
    }
    if (payload.income || payload.expense) {
      return [
        { label: "Income", data: payload.income || [], backgroundColor: "#66FF99", borderColor: "#66FF99", borderWidth: 1.5 },
        { label: "Expense", data: payload.expense || [], backgroundColor: "#ff5577", borderColor: "#ff5577", borderWidth: 1.5 },
      ];
    }
    const values = payload.values || [];
    if (chartType === "doughnut" || chartType === "pie") {
      const colors = values.map((_, i) => RETRO_PALETTE[i % RETRO_PALETTE.length]);
      return [{ label: "Breakdown", data: values, backgroundColor: colors, borderColor: "#020804", borderWidth: 1 }];
    }
    if (chartType === "line") {
      return [{ label: "Trend", data: values, backgroundColor: "rgba(102, 255, 153, 0.18)", borderColor: "#66FF99", borderWidth: 2.5 }];
    }
    return [{ label: "Amount", data: values, backgroundColor: "#66FF99", borderColor: "#33CC66", borderWidth: 1.5 }];
  }

  let chartEnginePromise = null;

  function ensureChartEngine() {
    if (typeof window.Chart !== "undefined") {
      return Promise.resolve();
    }
    if (chartEnginePromise) {
      return chartEnginePromise;
    }
    chartEnginePromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/static/vendor/chart.min.js";
      script.defer = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error("Chart engine failed to load."));
      document.head.appendChild(script);
    });
    return chartEnginePromise;
  }

  function bootCharts() {
    const canvases = Array.from(document.querySelectorAll("canvas[data-chart]"));
    if (!canvases.length) return Promise.resolve();
    return ensureChartEngine().then(() => {
      canvases.forEach((canvas) => {
      if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
      }
      const chartType = canvas.dataset.chart || "bar";
      const payload = parsePayload(canvas);
      const labels = payload.labels || [];
      const datasets = normalizeDatasets(payload, chartType);
      const xTitle = canvas.dataset.xTitle || "Period / Category";
      const yTitle = canvas.dataset.yTitle || "Amount (₹)";

      try {
        canvas.chartInstance = new window.Chart(canvas, {
          type: chartType,
          data: { labels: labels, datasets: datasets },
          options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: chartType !== "doughnut" && chartType !== "pie" && datasets.length > 1,
                labels: { color: "#e5ffe9", font: { family: "'VT323', 'IBM Plex Mono', monospace", size: 18 } }
              },
              tooltip: {
                backgroundColor: "rgba(5, 20, 8, 0.95)",
                borderColor: "#66FF99",
                borderWidth: 1,
                titleFont: { family: "'VT323', 'IBM Plex Mono', monospace", size: 19 },
                bodyFont: { family: "'VT323', 'IBM Plex Mono', monospace", size: 18 },
                callbacks: {
                  label: function (context) {
                    let label = context.dataset.label || "";
                    if (label) label += ": ";
                    const val = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                    if (typeof val === "number") {
                      if (chartType === "doughnut" || chartType === "pie") {
                        return label + "₹" + val.toLocaleString("en-IN");
                      }
                      return label + "₹" + val.toLocaleString("en-IN");
                    }
                    return label + val;
                  }
                }
              }
            },
            scales: chartType === "doughnut" || chartType === "pie" ? {} : {
              x: {
                title: {
                  display: true,
                  text: xTitle,
                  color: "#66FF99",
                  font: { family: "'VT323', 'IBM Plex Mono', monospace", size: 17, weight: "bold" }
                },
                ticks: { color: "#4faf70", font: { family: "'VT323', 'IBM Plex Mono', monospace", size: 16 } },
                grid: { color: "rgba(102,255,153,0.12)" }
              },
              y: {
                title: {
                  display: true,
                  text: yTitle,
                  color: "#66FF99",
                  font: { family: "'VT323', 'IBM Plex Mono', monospace", size: 17, weight: "bold" }
                },
                ticks: {
                  color: "#4faf70",
                  font: { family: "'VT323', 'IBM Plex Mono', monospace", size: 16 },
                  callback: function (val) {
                    if (val >= 10000000) return "₹" + (val / 10000000).toFixed(1) + "Cr";
                    if (val >= 100000) return "₹" + (val / 100000).toFixed(1) + "L";
                    if (val >= 1000) return "₹" + (val / 1000).toFixed(0) + "K";
                    return "₹" + val;
                  }
                },
                grid: { color: "rgba(102,255,153,0.12)" }
              }
            }
          }
        });
      } catch (err) {
        console.error("Error initializing chart on canvas", canvas, err);
      }
      });
    }).catch((err) => {
      console.error(err);
    });
  }

  /* ================================================================
     D-OS Centralized Global Activity & Loading Manager
     ================================================================ */
  const ActivityManager = {
    activeOps: {},
    opCounter: 0,
    hudEl: null,
    hudMsgEl: null,
    hudBarEl: null,
    hudMetaEl: null,
    isOnline: typeof navigator !== "undefined" ? navigator.onLine !== false : true,
    htmxOps: typeof WeakMap !== "undefined" ? new WeakMap() : null,
    debugLog: [],

    init: function () {
      this._createHud();
      this._bindNetworkEvents();
      this._bindFormSubmissions();
      this._bindDownloadEvents();
      this._bindNavigationEvents();
      this._bindHtmxEvents();
      this._bindBackForwardCacheGuard();
    },

    _createHud: function () {
      if (document.getElementById("terminal-activity-hud")) {
        this.hudEl = document.getElementById("terminal-activity-hud");
        this.hudMsgEl = document.getElementById("hud-status-msg");
        this.hudBarEl = document.getElementById("hud-scanner-bar");
        this.hudMetaEl = document.getElementById("hud-meta-info");
        return;
      }
      const hud = document.createElement("aside");
      hud.id = "terminal-activity-hud";
      hud.className = "terminal-activity-hud";
      hud.setAttribute("aria-live", "polite");
      hud.setAttribute("role", "status");
      hud.innerHTML = [
        '<div class="hud-inner">',
        '  <div class="hud-header">',
        '    <span class="hud-pulse blink">●</span>',
        '    <span id="hud-status-msg" class="hud-status-msg">SYSTEM ACTIVITY // PROCESSING...</span>',
        '  </div>',
        '  <div class="hud-bar-wrap">',
        '    <span id="hud-scanner-bar" class="hud-scanner-bar">[■■■■□□□□□□□□]</span>',
        '  </div>',
        '  <div id="hud-meta-info" class="hud-meta-info">STATUS: ACTIVE · DURATION: 0.0s</div>',
        '</div>'
      ].join("");
      document.body.appendChild(hud);
      this.hudEl = hud;
      this.hudMsgEl = document.getElementById("hud-status-msg");
      this.hudBarEl = document.getElementById("hud-scanner-bar");
      this.hudMetaEl = document.getElementById("hud-meta-info");
    },

    _bindNetworkEvents: function () {
      const self = this;
      window.addEventListener("online", function () {
        self.isOnline = true;
        self._notifyNetworkChange(true);
      });
      window.addEventListener("offline", function () {
        self.isOnline = false;
        self._notifyNetworkChange(false);
      });
    },

    _notifyNetworkChange: function (online) {
      if (!online) {
        this.start("SYSTEM_OFFLINE", {
          message: "SYSTEM ALERT // NO NETWORK CONNECTION DETECTED",
          level: "page"
        });
      } else {
        this.complete("SYSTEM_OFFLINE");
      }
    },

    _bindFormSubmissions: function () {
      const self = this;
      document.addEventListener("submit", function (evt) {
        const form = evt.target;
        if (!form || form.tagName !== "FORM") return;
        if (evt.defaultPrevented) return;
        if (form.hasAttribute("hx-get") || form.hasAttribute("hx-post")) return;

        // Skip search instant suggestions if handled by HTMX input keyup
        if (form.classList.contains("global-search") && evt.submitter && evt.submitter.type !== "submit") {
          return;
        }

        const submitBtn = evt.submitter || form.querySelector('button[type="submit"], input[type="submit"]');

        // Strictly prevent double submission
        if (form.dataset.submitting === "true") {
          evt.preventDefault();
          return false;
        }
        form.dataset.submitting = "true";

        const opName = form.getAttribute("data-op-name") || self._inferOpName(form, submitBtn);
        const opId = "form_" + (++self.opCounter);

        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add("submitting");
          if (!submitBtn.dataset.origText) {
            submitBtn.dataset.origText = submitBtn.innerHTML;
          }
          submitBtn.innerHTML = '<span class="blink">►</span> ' + self._inferButtonLoadingText(form, submitBtn);
        }

        self.start(opId, {
          message: opName,
          level: "inline",
          form: form,
          btn: submitBtn,
          requestType: "FORM"
        });
      });
    },

    _inferOpName: function (form, btn) {
      const act = (form.action || "").toLowerCase();
      const btnText = (btn ? btn.textContent : "").toLowerCase().trim();
      if (act.indexOf("/transactions") !== -1 || act.indexOf("/expenses") !== -1 || act.indexOf("/income") !== -1) {
        return "SAVING TRANSACTION...";
      }
      if (act.indexOf("/budget/custom") !== -1) {
        if (act.indexOf("/delete") !== -1) return "DELETING CUSTOM BUDGET...";
        if (act.indexOf("/expense") !== -1) return "LOGGING BUDGET EXPENSE...";
        return "CREATING CUSTOM BUDGET...";
      }
      if (act.indexOf("/budget") !== -1) {
        return "UPDATING BUDGET ALLOCATION...";
      }
      if (act.indexOf("/goals") !== -1) {
        if (act.indexOf("/delete") !== -1) return "REMOVING FINANCIAL GOAL...";
        if (act.indexOf("/add-money") !== -1) return "ALLOCATING GOAL FUNDS...";
        return "SAVING FINANCIAL GOAL...";
      }
      if (act.indexOf("/lend-borrow") !== -1) {
        return "RECORDING LOAN TRANSACTION...";
      }
      if (act.indexOf("/settings") !== -1) {
        return "UPDATING SYSTEM SETTINGS...";
      }
      if (act.indexOf("/login") !== -1 || act.indexOf("/auth") !== -1) {
        return "AUTHENTICATING ACCESS CREDENTIALS...";
      }
      if (act.indexOf("/logout") !== -1) {
        return "TERMINATING SESSION...";
      }
      if (btnText.indexOf("delete") !== -1 || btnText.indexOf("remove") !== -1) {
        return "DELETING RECORD...";
      }
      return "PROCESSING OPERATION...";
    },

    _inferButtonLoadingText: function (form, btn) {
      const act = (form.action || "").toLowerCase();
      const btnText = (btn ? btn.textContent : "").toLowerCase();
      if (btnText.indexOf("delete") !== -1 || btnText.indexOf("remove") !== -1) {
        return "[ DELETING... ]";
      }
      if (btnText.indexOf("calculate") !== -1) {
        return "[ CALCULATING... ]";
      }
      if (btnText.indexOf("filter") !== -1 || btnText.indexOf("search") !== -1) {
        return "[ SEARCHING... ]";
      }
      return "[ PROCESSING... ]";
    },

    _bindDownloadEvents: function () {
      const self = this;
      document.addEventListener("click", function (evt) {
        const link = evt.target.closest("a[data-download]");
        if (!link) return;
        const href = link.getAttribute("href");
        if (!href || link.dataset.submitting === "true") {
          evt.preventDefault();
          return;
        }

        evt.preventDefault();
        const opId = "download_" + (++self.opCounter);
        const originalText = link.innerHTML;
        const opName = link.getAttribute("data-op-name") || self._inferDownloadOpName(link);
        link.dataset.submitting = "true";
        link.setAttribute("aria-disabled", "true");
        link.classList.add("submitting");
        link.innerHTML = '<span class="blink">►</span> [ EXPORTING... ]';

        self.start(opId, {
          message: opName,
          level: "inline",
          requestType: "DOWNLOAD"
        });

        const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        const downloadTimeout = setTimeout(function () {
          if (controller) controller.abort();
        }, 15000);

        fetch(href, { credentials: "same-origin", signal: controller ? controller.signal : undefined })
          .then(function (response) {
            clearTimeout(downloadTimeout);
            if (!response.ok) throw new Error("EXPORT FAILED");
            const disposition = response.headers.get("Content-Disposition") || "";
            const match = disposition.match(/filename="?([^"]+)"?/i);
            const fallback = href.indexOf(".pdf") !== -1 ? "dos-report.pdf" : "dos-export.csv";
            const filename = match ? match[1] : fallback;
            return response.blob().then(function (blob) {
              return { blob: blob, filename: filename };
            });
          })
          .then(function (file) {
            const url = URL.createObjectURL(file.blob);
            const temp = document.createElement("a");
            temp.href = url;
            temp.download = file.filename;
            temp.setAttribute("download", file.filename);
            temp.setAttribute("data-download", "true");
            temp.style.display = "none";
            temp.addEventListener("click", function (e) {
              e.stopPropagation();
            });
            document.body.appendChild(temp);
            temp.click();
            temp.remove();
            setTimeout(function () {
              URL.revokeObjectURL(url);
            }, 1000);
            self.complete(opId, "EXPORT READY");
          })
          .catch(function () {
            clearTimeout(downloadTimeout);
            self.fail(opId, "EXPORT FAILED");
          })
          .finally(function () {
            link.dataset.submitting = "false";
            link.removeAttribute("aria-disabled");
            link.classList.remove("submitting");
            link.innerHTML = originalText;
          });
      });
    },

    _inferDownloadOpName: function (link) {
      const href = (link.getAttribute("href") || "").toLowerCase();
      if (href.indexOf(".pdf") !== -1) return "GENERATING PDF REPORT...";
      if (href.indexOf(".csv") !== -1) return "EXPORTING CSV DATA...";
      return "PREPARING DOWNLOAD...";
    },

    _bindNavigationEvents: function () {
      const self = this;
      document.addEventListener("click", function (evt) {
        const anchor = evt.target.closest("a[href]");
        if (!anchor) return;
        if (anchor.hasAttribute("data-download") || anchor.hasAttribute("download")) return;
        const href = anchor.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("blob:") || href.startsWith("data:") || anchor.target === "_blank") {
          return;
        }
        if (href === window.location.pathname) return;

        let msg = "LOADING SYSTEM VIEW...";
        if (href === "/" || href.startsWith("/?")) msg = "LOADING FINANCIAL DATA...";
        else if (href.startsWith("/money")) msg = "RETRIEVING TRANSACTIONS...";
        else if (href.startsWith("/visualize")) msg = "LOADING ANALYTICS DATA...";
        else if (href.startsWith("/budget")) msg = "LOADING BUDGET DATA...";
        else if (href.startsWith("/goals")) msg = "RETRIEVING GOALS...";
        else if (href.startsWith("/reports")) msg = "GENERATING REPORT DATA...";
        else if (href.startsWith("/lend-borrow")) msg = "RETRIEVING LOAN RECORDS...";
        else if (href.startsWith("/settings")) msg = "RETRIEVING SETTINGS...";

        const navOpId = "nav_" + (++self.opCounter);
        self.start(navOpId, {
          message: msg,
          level: "navigation",
          delayShowMs: 220
        });
      });
    },

    _bindHtmxEvents: function () {
      const self = this;
      document.body.addEventListener("htmx:beforeRequest", function (evt) {
        const el = evt.detail.elt;
        const form = el.tagName === "FORM" ? el : el.closest("form");

        // Suppress screen-level Activity HUD for search/filter operations to keep them smooth
        const isFilterOrSearch = form && (
          form.classList.contains("filter-row") ||
          form.classList.contains("ledger-filter-panel") ||
          form.classList.contains("report-filter-form") ||
          form.hasAttribute("data-no-hud") ||
          form.classList.contains("global-search")
        );
        if (isFilterOrSearch) {
          return;
        }

        const submitBtn = form ? form.querySelector('button[type="submit"], input[type="submit"]') : null;
        if (form && form.dataset.submitting === "true") {
          evt.preventDefault();
          return;
        }
        if (form) form.dataset.submitting = "true";
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add("submitting");
          if (!submitBtn.dataset.origText) submitBtn.dataset.origText = submitBtn.innerHTML;
          submitBtn.innerHTML = '<span class="blink">►</span> ' + self._inferButtonLoadingText(form, submitBtn);
        }

        const opName = el.getAttribute("data-op-name") || (form && form.getAttribute("data-op-name")) || "FETCHING DATA...";
        const opId = "htmx_" + (++self.opCounter);
        if (self.htmxOps) self.htmxOps.set(el, opId);
        else el.dataset.activityOpId = opId;
        self.start(opId, {
          message: opName,
          level: "component",
          element: el,
          form: form,
          btn: submitBtn,
          requestType: "HTMX"
        });
      });

      document.body.addEventListener("htmx:afterRequest", function (evt) {
        const opId = evt.detail ? (self.htmxOps ? self.htmxOps.get(evt.detail.elt) : evt.detail.elt.dataset.activityOpId) : null;
        if (opId) {
          self.complete(opId);
          if (self.htmxOps) self.htmxOps.delete(evt.detail.elt);
          else delete evt.detail.elt.dataset.activityOpId;
        }
      });

      document.body.addEventListener("htmx:responseError", function (evt) {
        const opId = evt.detail ? (self.htmxOps ? self.htmxOps.get(evt.detail.elt) : evt.detail.elt.dataset.activityOpId) : null;
        if (opId) {
          self.fail(opId, "REQUEST FAILED");
          if (self.htmxOps) self.htmxOps.delete(evt.detail.elt);
          else delete evt.detail.elt.dataset.activityOpId;
        }
      });

      document.body.addEventListener("htmx:sendError", function (evt) {
        const opId = evt.detail ? (self.htmxOps ? self.htmxOps.get(evt.detail.elt) : evt.detail.elt.dataset.activityOpId) : null;
        if (opId) {
          self.fail(opId, "NETWORK CONNECTION ERROR");
          if (self.htmxOps) self.htmxOps.delete(evt.detail.elt);
          else delete evt.detail.elt.dataset.activityOpId;
        }
      });
    },

    start: function (opId, options) {
      options = options || {};
      const now = Date.now();
      const self = this;
      const op = {
        id: opId,
        message: options.message || "SYSTEM ACTIVITY IN PROGRESS...",
        level: options.level || "inline",
        startTime: now,
        delayShowMs: options.delayShowMs || 0,
        element: options.element || null,
        btn: options.btn || null,
        form: options.form || null,
        requestType: options.requestType || "ASYNC"
      };

      // Watchdog timeout guarantees NO loader can ever hang indefinitely on screen
      op.safetyTimeout = setTimeout(function () {
        if (self.activeOps[opId]) {
          console.warn("ActivityManager auto-clearing timed-out op:", opId);
          self.complete(opId);
        }
      }, 15000);

      this.activeOps[opId] = op;
      this._recordDebug(op, "STARTED");
      this._updateHudView();
    },

    update: function (opId, statusMsg) {
      if (this.activeOps[opId]) {
        this.activeOps[opId].message = statusMsg;
        this._updateHudView();
      }
    },

    complete: function (opId, successMsg) {
      const op = this.activeOps[opId];
      if (!op) return;

      if (op.safetyTimeout) {
        clearTimeout(op.safetyTimeout);
        op.safetyTimeout = null;
      }

      if (op.btn && op.form) {
        op.form.dataset.submitting = "false";
        op.btn.disabled = false;
        op.btn.classList.remove("submitting");
        if (successMsg) {
          op.btn.innerHTML = "✓ " + successMsg;
          setTimeout(function () {
            if (op.btn.dataset.origText) {
              op.btn.innerHTML = op.btn.dataset.origText;
            }
          }, 1500);
        } else if (op.btn.dataset.origText) {
          op.btn.innerHTML = op.btn.dataset.origText;
        }
      }

      this._recordDebug(op, "SUCCESS");
      delete this.activeOps[opId];
      this._updateHudView();
    },

    fail: function (opId, errorMsg) {
      const op = this.activeOps[opId];
      if (!op) return;

      if (op.safetyTimeout) {
        clearTimeout(op.safetyTimeout);
        op.safetyTimeout = null;
      }

      if (op.btn && op.form) {
        op.form.dataset.submitting = "false";
        op.btn.disabled = false;
        op.btn.classList.remove("submitting");
        op.btn.innerHTML = "✕ " + (errorMsg || "FAILED");
        setTimeout(function () {
          if (op.btn.dataset.origText) {
            op.btn.innerHTML = op.btn.dataset.origText;
          }
        }, 2500);
      }

      op.error = errorMsg || "FAILED";
      this._recordDebug(op, "FAILED");
      delete this.activeOps[opId];
      this._updateHudView();
    },

    _updateHudView: function () {
      const keys = Object.keys(this.activeOps);
      if (!keys.length) {
        if (this.hudEl) {
          this.hudEl.classList.remove("visible", "slow", "warning");
        }
        if (this._scanInterval) {
          clearInterval(this._scanInterval);
          this._scanInterval = null;
        }
        return;
      }

      const topOp = this.activeOps[keys[keys.length - 1]];
      if (!this.hudEl) this._createHud();

      const elapsed = (Date.now() - topOp.startTime) / 1000;
      if (topOp.delayShowMs > 0 && elapsed * 1000 < topOp.delayShowMs) {
        const self = this;
        setTimeout(function () { self._updateHudView(); }, topOp.delayShowMs);
        return;
      }

      this.hudEl.classList.add("visible");
      if (this.hudMsgEl) {
        this.hudMsgEl.textContent = topOp.message;
      }

      this._renderStatusMeta(topOp, elapsed);

      if (!this._scanInterval) {
        const self = this;
        let frame = 0;
        const SCAN_FRAMES = [
          "[████░░░░░░░░]",
          "[░████░░░░░░░]",
          "[░░████░░░░░░]",
          "[░░░████░░░░░]",
          "[░░░░████░░░░]",
          "[░░░░░████░░░]",
          "[░░░░░░████░░]",
          "[░░░░░░░████░]",
          "[░░░░░░░░████]",
          "[░░░░░░░████░]",
          "[░░░░░░████░░]",
          "[░░░░░████░░░]",
          "[░░░░████░░░░]",
          "[░░░████░░░░░]",
          "[░░████░░░░░░]",
          "[░████░░░░░░░]"
        ];
        this._scanInterval = setInterval(function () {
          const activeKeys = Object.keys(self.activeOps);
          if (!activeKeys.length) {
            clearInterval(self._scanInterval);
            self._scanInterval = null;
            return;
          }
          const currentOp = self.activeOps[activeKeys[activeKeys.length - 1]];
          const curElapsed = (Date.now() - currentOp.startTime) / 1000;

          frame = (frame + 1) % SCAN_FRAMES.length;
          if (self.hudBarEl) {
            self.hudBarEl.textContent = SCAN_FRAMES[frame];
          }
          self._renderStatusMeta(currentOp, curElapsed);
        }, 110);
      }
    },

    _renderStatusMeta: function (op, elapsed) {
      if (!this.hudMetaEl) return;
      const durationStr = elapsed.toFixed(1) + "s";
      let statusNote = "STATUS: ACTIVE";

      if (!this.isOnline) {
        statusNote = "STATUS: OFFLINE // NO NETWORK CONNECTION DETECTED";
        if (this.hudEl) this.hudEl.classList.add("warning");
      } else if (this._connectionLooksSlow()) {
        statusNote = "STATUS: ACTIVE // NETWORK CONNECTION APPEARS SLOW";
        if (this.hudEl) this.hudEl.classList.add("slow");
      } else if (elapsed > 5.0) {
        statusNote = "STATUS: ACTIVE // SERVER RESPONSE IS TAKING LONGER THAN EXPECTED";
        if (this.hudEl) this.hudEl.classList.add("slow");
      } else if (elapsed > 2.5) {
        statusNote = "STATUS: ACTIVE // REQUEST TAKING LONGER THAN EXPECTED";
        if (this.hudEl) this.hudEl.classList.add("slow");
      } else {
        if (this.hudEl) this.hudEl.classList.remove("slow", "warning");
      }

      this.hudMetaEl.textContent = statusNote + " · DURATION: " + durationStr;
    },

    _connectionLooksSlow: function () {
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (!connection) return false;
      const effectiveType = String(connection.effectiveType || "").toLowerCase();
      if (effectiveType === "slow-2g" || effectiveType === "2g") return true;
      if (typeof connection.downlink === "number" && connection.downlink > 0 && connection.downlink < 0.7) return true;
      if (typeof connection.rtt === "number" && connection.rtt > 900) return true;
      return false;
    },

    _recordDebug: function (op, status) {
      const now = Date.now();
      const entry = {
        operation: op.id,
        message: op.message,
        requestType: op.requestType,
        startedAt: new Date(op.startTime).toISOString(),
        completedAt: status === "STARTED" ? null : new Date(now).toISOString(),
        durationMs: status === "STARTED" ? 0 : now - op.startTime,
        status: status,
        network: this.isOnline ? "ONLINE" : "OFFLINE",
        error: op.error || null
      };
      this.debugLog.push(entry);
      if (this.debugLog.length > 50) this.debugLog.shift();
      try {
        if (window.localStorage && window.localStorage.getItem("DOS_DEBUG_ACTIVITY") === "true") {
          console.debug("[D-OS Activity]", entry);
        }
      } catch (error) {
        // localStorage can be blocked in some privacy modes; activity tracking still works.
      }
    },

    _bindBackForwardCacheGuard: function () {
      window.addEventListener("pageshow", function (event) {
        if (event.persisted && document.body.classList.contains("terminal-body")) {
          window.location.reload();
        }
      });
    }
  };

  /* ================================================================
     Unified Transaction Form & Visual Category Selector
     ================================================================ */
  function initTransactionSwitchers() {
    document.querySelectorAll("[data-transaction-switcher]").forEach((container) => {
      const form = container.closest("form");
      if (!form) return;

      const typeInput = form.querySelector('input[name="type"]');
      const categorySelect = form.querySelector('select[name="category_id"]');
      const buttons = container.querySelectorAll("[data-type-btn]");
      const catTiles = form.querySelectorAll(".category-tile-btn");

      function syncCategoryTiles(selectedType, selectedCatId) {
        let firstMatchId = null;
        catTiles.forEach((tile) => {
          const kind = tile.getAttribute("data-kind") || "expense";
          const catId = tile.getAttribute("data-cat-id");
          if (kind === selectedType || kind === "both" || !kind) {
            tile.style.display = "inline-flex";
            if (!firstMatchId) firstMatchId = catId;
          } else {
            tile.style.display = "none";
          }
        });

        const targetCatId = selectedCatId || firstMatchId;
        catTiles.forEach((tile) => {
          if (tile.getAttribute("data-cat-id") === targetCatId) {
            tile.classList.add("active");
          } else {
            tile.classList.remove("active");
          }
        });
        if (categorySelect && targetCatId) {
          categorySelect.value = targetCatId;
        }
      }

      function applyType(selectedType) {
        if (typeInput) typeInput.value = selectedType;
        buttons.forEach((btn) => {
          if (btn.getAttribute("data-type-btn") === selectedType) {
            btn.classList.add("active");
          } else {
            btn.classList.remove("active");
          }
        });

        if (categorySelect) {
          let firstMatch = null;
          Array.from(categorySelect.options).forEach((opt) => {
            const optType = opt.getAttribute("data-kind") || "expense";
            if (optType === selectedType || optType === "both" || !opt.value) {
              opt.hidden = false;
              opt.disabled = false;
              if (!firstMatch && opt.value) firstMatch = opt.value;
            } else {
              opt.hidden = true;
              opt.disabled = true;
            }
          });
          if (firstMatch && (categorySelect.selectedOptions[0]?.disabled || !categorySelect.value)) {
            categorySelect.value = firstMatch;
          }
          syncCategoryTiles(selectedType, categorySelect.value || firstMatch);
        }

        // Adjust form submit button accent
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
          if (selectedType === "income") {
            submitBtn.textContent = "+ Record Income";
            submitBtn.style.borderColor = "var(--green)";
          } else {
            submitBtn.textContent = "- Record Expense";
            submitBtn.style.borderColor = "var(--red)";
          }
        }
      }

      buttons.forEach((btn) => {
        if (btn.dataset.boundSwitcher === "true") return;
        btn.dataset.boundSwitcher = "true";
        btn.addEventListener("click", function () {
          applyType(this.getAttribute("data-type-btn"));
        });
      });

      catTiles.forEach((tile) => {
        if (tile.dataset.boundTile === "true") return;
        tile.dataset.boundTile = "true";
        tile.addEventListener("click", function () {
          const catId = this.getAttribute("data-cat-id");
          if (categorySelect && catId) {
            categorySelect.value = catId;
          }
          catTiles.forEach((t) => t.classList.remove("active"));
          this.classList.add("active");
        });
      });

      if (categorySelect && categorySelect.dataset.boundSelect !== "true") {
        categorySelect.dataset.boundSelect = "true";
        categorySelect.addEventListener("change", function () {
          const selectedVal = this.value;
          catTiles.forEach((tile) => {
            if (tile.getAttribute("data-cat-id") === selectedVal) {
              tile.classList.add("active");
            } else {
              tile.classList.remove("active");
            }
          });
        });
      }

      // Initial apply
      const initialType = typeInput ? typeInput.value || "expense" : "expense";
      applyType(initialType);
    });

    // Modal open / close handlers
    document.addEventListener("click", function (evt) {
      const openBtn = evt.target.closest("[data-open-modal]");
      if (openBtn) {
        const modalId = openBtn.getAttribute("data-open-modal");
        const modal = document.getElementById(modalId);
        if (modal) {
          modal.classList.add("open");
          const firstInput = modal.querySelector("input:not([type=hidden]), select");
          if (firstInput) firstInput.focus();
        }
      }

      const closeBtn = evt.target.closest("[data-close-modal]");
      if (closeBtn) {
        const modal = closeBtn.closest(".terminal-modal-backdrop");
        if (modal) modal.classList.remove("open");
      }
    });

    // Close modal on Escape key
    document.addEventListener("keydown", function (evt) {
      if (evt.key === "Escape") {
        document.querySelectorAll(".terminal-modal-backdrop.open").forEach((m) => m.classList.remove("open"));
      }
    });
  }

  function initQuickAmounts() {
    document.querySelectorAll("[data-quick-amount]").forEach((button) => {
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";
      button.addEventListener("click", function () {
        const form = this.closest("form");
        const amountInput = form ? form.querySelector('input[name="amount"]') : null;
        if (amountInput) {
          amountInput.value = this.getAttribute("data-quick-amount") || "";
          amountInput.focus();
        }
      });
    });
  }

  // --- Password Visibility Toggle ---
  function initPasswordToggles() {
    var eyeOpen = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
    var eyeSlash = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

    document.querySelectorAll("[data-toggle-password]").forEach((btn) => {
      if (btn.dataset.bound === "true") return;
      btn.dataset.bound = "true";
      btn.innerHTML = eyeOpen;
      btn.addEventListener("click", function () {
        const wrap = this.closest(".password-input-wrap");
        if (!wrap) return;
        const input = wrap.querySelector("input");
        if (!input) return;
        if (input.type === "password") {
          input.type = "text";
          this.innerHTML = eyeSlash;
          this.setAttribute("aria-label", "Hide password");
          this.setAttribute("title", "Hide password");
          this.classList.add("active");
        } else {
          input.type = "password";
          this.innerHTML = eyeOpen;
          this.setAttribute("aria-label", "Show password");
          this.setAttribute("title", "Show password");
          this.classList.remove("active");
        }
      });
    });
  }

  // --- Onboarding Tour Module ---
  function initOnboardingTour() {
    const overlay = document.getElementById("onboarding-overlay");
    if (!overlay) return;

    const steps = Array.from(overlay.querySelectorAll("[data-onboarding-step]"));
    if (!steps.length) return;

    let currentStep = 0;

    function showStep(index) {
      if (index < 0) index = 0;
      if (index >= steps.length) {
        completeTour();
        return;
      }
      currentStep = index;
      steps.forEach((s, i) => {
        if (i === currentStep) {
          s.classList.add("active");
        } else {
          s.classList.remove("active");
        }
      });
    }

    function completeTour() {
      overlay.style.transition = "opacity 0.2s ease";
      overlay.style.opacity = "0";
      setTimeout(() => {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }, 200);

      try {
        localStorage.setItem("dos_onboarding_completed", "true");
      } catch (e) {}

      fetch("/api/onboarding-complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }).catch((err) => {
        console.warn("Could not save onboarding status:", err);
      });
    }

    overlay.addEventListener("click", function (event) {
      const actionBtn = event.target.closest("[data-onboarding-action]");
      if (!actionBtn) return;

      const action = actionBtn.getAttribute("data-onboarding-action");
      if (action === "next") {
        showStep(currentStep + 1);
      } else if (action === "back") {
        showStep(currentStep - 1);
      } else if (action === "skip" || action === "complete") {
        completeTour();
      }
    });
  }

  // --- Help Search Filter Module ---
  function initHelpSearch() {
    const searchInput = document.getElementById("help-search-input");
    const container = document.getElementById("help-articles");
    const noResults = document.getElementById("help-no-results");
    if (!searchInput || !container) return;

    const sections = Array.from(container.querySelectorAll("[data-help-section]"));
    const articles = Array.from(container.querySelectorAll("[data-help-article]"));

    searchInput.addEventListener("input", function () {
      const query = this.value.trim().toLowerCase();

      if (!query) {
        sections.forEach((sec) => (sec.style.display = ""));
        articles.forEach((art) => {
          art.style.display = "";
          art.open = false;
        });
        if (noResults) noResults.style.display = "none";
        return;
      }

      let totalMatches = 0;

      sections.forEach((section) => {
        const secArticles = Array.from(section.querySelectorAll("[data-help-article]"));
        let secMatches = 0;

        secArticles.forEach((art) => {
          const text = (art.textContent || "").toLowerCase();
          if (text.includes(query)) {
            art.style.display = "";
            art.open = true;
            secMatches++;
            totalMatches++;
          } else {
            art.style.display = "none";
            art.open = false;
          }
        });

        section.style.display = secMatches > 0 ? "" : "none";
      });

      if (noResults) {
        noResults.style.display = totalMatches === 0 ? "block" : "none";
      }
    });
  }

  // Dismiss button for warning banners
  document.addEventListener("click", function (event) {
    const btn = event.target.closest("[data-dismiss]");
    if (btn) {
      const parent = btn.closest("[data-dismissible]") || btn.parentElement;
      if (parent) {
        parent.style.display = "none";
        parent.remove();
      }
    }
  });

  if (typeof window !== "undefined") {
    window.ActivityManager = ActivityManager;
  }

  ready(function () {
    setDefaultDates();
    ActivityManager.init();
    initTransactionSwitchers();
    initQuickAmounts();
    initPasswordToggles();
    initOnboardingTour();
    initHelpSearch();
    bootCharts();
  });

  document.body.addEventListener("htmx:afterSwap", function () {
    initTransactionSwitchers();
    initQuickAmounts();
    initPasswordToggles();
    bootCharts();
  });
})();
