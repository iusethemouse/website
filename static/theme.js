(function () {
    "use strict";

    var allowedThemes = ["", "theme-beige", "theme-dark"];
    var root = document.documentElement;
    var storedTheme = "";

    try {
        storedTheme = localStorage.getItem("theme") || "";
    } catch (_) {
        storedTheme = "";
    }

    if (allowedThemes.indexOf(storedTheme) !== -1 && storedTheme) {
        root.classList.add(storedTheme);
    }

    function applyTheme(theme) {
        root.classList.remove("theme-beige", "theme-dark");
        if (theme) root.classList.add(theme);

        try {
            if (theme) localStorage.setItem("theme", theme);
            else localStorage.removeItem("theme");
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
        applyTheme(allowedThemes.indexOf(storedTheme) !== -1 ? storedTheme : "");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setUpButtons);
    } else {
        setUpButtons();
    }
})();
