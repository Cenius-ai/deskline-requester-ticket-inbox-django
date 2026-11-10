/* Once-a-minute SLA label tick. The server renders the first state; this keeps
   the countdown honest while a queue or a ticket stays open. */
(function () {
  "use strict";

  var STATE_LABELS = {
    on_track: "On track",
    due_soon: "Due soon",
    overdue: "Overdue"
  };
  var DEFAULT_DUE_SOON_MS = 4 * 60 * 60 * 1000;

  function humanize(minutes) {
    var total = Math.max(Math.round(minutes), 0);
    var days = Math.floor(total / 1440);
    var hours = Math.floor((total % 1440) / 60);
    var mins = total % 60;
    if (days > 0) {
      return hours > 0 ? days + "d " + hours + "h" : days + "d";
    }
    if (hours > 0 && mins > 0) {
      return hours + "h " + (mins < 10 ? "0" + mins : String(mins)) + "m";
    }
    if (hours > 0) {
      return hours + "h";
    }
    return mins + "m";
  }

  function resolveDueSoonWindow() {
    var raw = document.body && document.body.getAttribute("data-sla-due-soon-hours");
    var hours = raw ? parseFloat(raw) : NaN;
    if (!isNaN(hours) && hours > 0) {
      return hours * 60 * 60 * 1000;
    }
    return DEFAULT_DUE_SOON_MS;
  }

  function stateFor(remainingMs, dueSoonMs) {
    if (remainingMs <= 0) {
      return "overdue";
    }
    if (remainingMs <= dueSoonMs) {
      return "due_soon";
    }
    return "on_track";
  }

  function refresh() {
    var dueSoonMs = resolveDueSoonWindow();
    var now = Date.now();
    var badges = document.querySelectorAll("[data-sla-due]");
    Array.prototype.forEach.call(badges, function (badge) {
      var dueMs = Date.parse(badge.getAttribute("data-sla-due") || "");
      if (isNaN(dueMs)) {
        return;
      }
      var remaining = dueMs - now;
      var state = stateFor(remaining, dueSoonMs);
      var minutes = Math.abs(remaining) / 60000;
      var label = humanize(minutes) + (remaining <= 0 ? " overdue" : " left");

      var stateEl = badge.querySelector("[data-sla-state-label]");
      var labelEl = badge.querySelector("[data-sla-label]");
      if (stateEl) {
        stateEl.textContent = STATE_LABELS[state];
      }
      if (labelEl) {
        labelEl.textContent = label;
      }
      ["on_track", "due_soon", "overdue"].forEach(function (name) {
        badge.classList.toggle("sla--" + name, name === state);
      });
      badge.setAttribute("data-sla-state", state);
    });
  }

  refresh();
  window.setInterval(refresh, 60000);
})();
