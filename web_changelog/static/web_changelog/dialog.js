// Oeffnet den Was-ist-neu-Dialog. Bewusst ohne jede Entscheidungslogik: ob
// etwas anliegt, hat der Server bereits entschieden, sonst waere das Markup
// gar nicht erst da. Doppelte Regeln in zwei Sprachen laufen auseinander.
(function () {
  var dialog = document.querySelector("[data-wc-dialog]");
  if (!dialog) return;

  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }

  var schliessen = dialog.querySelector("[data-wc-schliessen]");
  if (schliessen) {
    schliessen.addEventListener("click", function () {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    });
  }
})();
