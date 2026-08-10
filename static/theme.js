(function () {
    "use strict";

    var allowedThemes = ["", "theme-beige", "theme-dark"];
    var defaultTheme = "theme-beige";
    var root = document.documentElement;
    var storedTheme = null;

    try {
        storedTheme = localStorage.getItem("theme");
    } catch (_) {
        storedTheme = null;
    }

    var initialTheme = allowedThemes.indexOf(storedTheme) !== -1
        ? storedTheme
        : defaultTheme;

    root.classList.remove("theme-beige", "theme-dark");
    if (initialTheme) root.classList.add(initialTheme);

    function applyTheme(theme) {
        root.classList.remove("theme-beige", "theme-dark");
        if (theme) root.classList.add(theme);

        try {
            localStorage.setItem("theme", theme);
        } catch (_) {
            // The theme still works for this page when storage is unavailable.
        }

        document.querySelectorAll(".theme-btn").forEach(function (button) {
            button.setAttribute("aria-pressed", String(button.dataset.theme === theme));
        });
    }

    function setUpButtons() {
        document.querySelectorAll(".theme-btn").forEach(function (button) {
            button.addEventListener("click", function () {
                applyTheme(button.dataset.theme || "");
            });
        });
        applyTheme(initialTheme);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setUpButtons);
    } else {
        setUpButtons();
    }
})();
