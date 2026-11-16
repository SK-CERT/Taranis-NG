"""The public web's page script: the colour mode, copying a feed's address, and in the template preview, the language menu.

The colour mode is light, dark, or as the browser says (the default). Every page carries the
script inline in its ``<head>``, so the mode is set before anything is drawn.
The page's mode button (``data-theme-toggle``) goes auto -> light -> dark -> auto, showing the
icon (``data-theme-icon``) and the label (``data-label-<mode>``) of the mode in use. The pick
is kept in the browser's storage, and "auto" follows the browser's setting as it changes.

The template preview in the GUI shows the page in a sandboxed frame that runs no other script:
core allows exactly this one by its hash (``SCRIPT_HASH``) in the preview page's
Content-Security-Policy. Such a frame has no storage, so there the pick lasts for the page; it
is also posted to the GUI, which opens the next rendering with it (``#theme=dark``).

A button with ``data-copy-link`` (the homepage's feed menu) puts that address on the clipboard and,
for a moment, shows a tick and its ``data-label-copied`` instead of its icon and ``data-label-copy``;
a ``data-copy-status`` element says it to screen readers. Without the Clipboard API (a page that is
not served securely) it copies through a hidden text field.

The preview's node marks the page (``data-taranis-preview`` on ``<html>``). Bootstrap's script
does not run there either, so this one opens the language menu, and a language picked in it
(``data-language-choice``) is posted to the GUI, which renders the preview in that language.
"""

import base64
import hashlib

SCRIPT = """
(function () {
    var KEY = "taranis-public-web-theme";
    var NEXT = { auto: "light", light: "dark", dark: "auto" };
    var media = window.matchMedia("(prefers-color-scheme: dark)");
    var stored = null;
    try {
        stored = window.localStorage.getItem(KEY);
    } catch (error) {
        // A sandboxed frame (the template preview) has no storage.
    }
    var asked = /(?:^#|&)theme=(auto|light|dark)(?:&|$)/.exec(window.location.hash);
    var choice = asked ? asked[1] : stored === "light" || stored === "dark" ? stored : "auto";

    function apply() {
        var dark = choice === "dark" || (choice === "auto" && media.matches);
        document.documentElement.setAttribute("data-bs-theme", dark ? "dark" : "light");
        var toggles = document.querySelectorAll("[data-theme-toggle]");
        for (var index = 0; index < toggles.length; index += 1) {
            var label = toggles[index].getAttribute("data-label-" + choice);
            if (label) {
                toggles[index].setAttribute("title", label);
                toggles[index].setAttribute("aria-label", label);
            }
            var icons = toggles[index].querySelectorAll("[data-theme-icon]");
            for (var iconIndex = 0; iconIndex < icons.length; iconIndex += 1) {
                icons[iconIndex].classList.toggle("d-none", icons[iconIndex].getAttribute("data-theme-icon") !== choice);
            }
        }
    }

    apply();
    if (typeof media.addEventListener === "function") {
        media.addEventListener("change", apply);
    } else if (typeof media.addListener === "function") {
        media.addListener(apply);
    }
    document.addEventListener("DOMContentLoaded", apply);
    document.addEventListener("click", function (event) {
        var toggle = event.target.closest ? event.target.closest("[data-theme-toggle]") : null;
        if (!toggle) {
            return;
        }
        choice = NEXT[choice];
        try {
            if (choice === "auto") {
                window.localStorage.removeItem(KEY);
            } else {
                window.localStorage.setItem(KEY, choice);
            }
        } catch (error) {
            // No storage: the pick lasts for this page.
        }
        if (window.parent !== window) {
            window.parent.postMessage({ taranisPublicWebTheme: choice }, "*");
        }
        apply();
    });

    function copied(button) {
        var icon = button.querySelector(".mdi");
        var status = document.querySelector("[data-copy-status]");
        var label = button.getAttribute("data-label-copied");
        if (icon) {
            icon.classList.replace("mdi-content-copy", "mdi-check");
        }
        button.setAttribute("title", label);
        if (status) {
            status.textContent = label;
        }
        window.setTimeout(function () {
            if (icon) {
                icon.classList.replace("mdi-check", "mdi-content-copy");
            }
            button.setAttribute("title", button.getAttribute("data-label-copy"));
            if (status) {
                status.textContent = "";
            }
        }, 1500);
    }

    function copyThroughField(text) {
        var field = document.createElement("textarea");
        field.value = text;
        field.setAttribute("readonly", "");
        field.style.position = "fixed";
        field.style.opacity = "0";
        document.body.appendChild(field);
        field.select();
        var done = false;
        try {
            done = document.execCommand("copy");
        } catch (error) {
            done = false;
        }
        document.body.removeChild(field);
        return done;
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest ? event.target.closest("[data-copy-link]") : null;
        if (!button) {
            return;
        }
        event.preventDefault();
        var link = button.getAttribute("data-copy-link");
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(link).then(
                function () {
                    copied(button);
                },
                function () {
                    if (copyThroughField(link)) {
                        copied(button);
                    }
                }
            );
        } else if (copyThroughField(link)) {
            copied(button);
        }
    });

    if (document.documentElement.hasAttribute("data-taranis-preview")) {
        document.addEventListener("click", function (event) {
            if (!event.target.closest) {
                return;
            }
            var language = event.target.closest("[data-language-choice]");
            if (language && window.parent !== window) {
                event.preventDefault();
                window.parent.postMessage({ taranisPublicWebLanguage: language.getAttribute("data-language-choice") }, "*");
            }
            var opener = event.target.closest('[data-bs-toggle="dropdown"]');
            var menu = opener ? opener.nextElementSibling : null;
            var shown = document.querySelectorAll(".dropdown-menu.show");
            for (var index = 0; index < shown.length; index += 1) {
                if (shown[index] !== menu) {
                    shown[index].classList.remove("show");
                    if (shown[index].previousElementSibling) {
                        shown[index].previousElementSibling.setAttribute("aria-expanded", "false");
                    }
                }
            }
            if (menu && menu.classList.contains("dropdown-menu")) {
                menu.setAttribute("data-bs-popper", "static");
                opener.setAttribute("aria-expanded", menu.classList.toggle("show") ? "true" : "false");
            }
        });
    }
})();
"""

# The CSP source that allows exactly this script, inline.
SCRIPT_HASH = "'sha256-" + base64.b64encode(hashlib.sha256(SCRIPT.encode("utf-8")).digest()).decode("ascii") + "'"
