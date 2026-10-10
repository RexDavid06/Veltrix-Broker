/* VELTRIX demo — small progressive-enhancement script. No frameworks. */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    /* Mobile navigation */
    var toggle = document.getElementById("mobileToggle");
    var nav = document.getElementById("mainNav");
    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        var open = nav.classList.toggle("open");
        toggle.setAttribute("aria-expanded", String(open));
      });
    }

    /* Trade form: live estimated amount */
    document.querySelectorAll("[data-trade-form]").forEach(function (form) {
      var price = parseFloat(form.getAttribute("data-price") || "0");
      var qtyInput = form.querySelector("[data-qty]");
      var out = form.querySelector("[data-amount]");
      function update() {
        if (!out || !qtyInput) return;
        var qty = parseFloat(qtyInput.value);
        if (!isFinite(qty) || qty <= 0) {
          out.textContent = "—";
          return;
        }
        out.textContent = (qty * price).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      }
      if (qtyInput) qtyInput.addEventListener("input", update);
      update();
    });

    /* Confirm simulated orders (they are labelled as simulated everywhere) */
    document.querySelectorAll("[data-confirm-sim]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        var side = form.querySelector("[name='side']");
        var label = side && side.value === "sell" ? "sell" : "buy";
        var message =
          "Submit this SIMULATED " +
          label +
          "? No real order is sent and no real money moves.";
        if (!window.confirm(message)) event.preventDefault();
      });
    });
  });
})();
