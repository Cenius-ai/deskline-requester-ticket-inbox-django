/* Deskline's only JavaScript outside the SLA label tick: the password
   show/hide toggle. Everything else is server-rendered Django templates. */
(function () {
  "use strict";

  var buttons = document.querySelectorAll("[data-reveal]");
  Array.prototype.forEach.call(buttons, function (button) {
    var field = document.getElementById(button.getAttribute("data-reveal"));
    if (!field) {
      return;
    }
    button.addEventListener("click", function () {
      var isVisible = field.getAttribute("type") === "text";
      field.setAttribute("type", isVisible ? "password" : "text");
      button.textContent = isVisible ? "Show" : "Hide";
      button.setAttribute("aria-pressed", isVisible ? "false" : "true");
      field.focus();
    });
  });
})();
