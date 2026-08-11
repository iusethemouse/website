(function () {
    "use strict";

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    function endpoint(reactionId) {
        return "/api/reactions/" + encodeURIComponent(reactionId);
    }

    async function requestReaction(reactionId, method) {
        var response = await fetch(endpoint(reactionId), {
            method: method,
            headers: { Accept: "application/json" },
            credentials: "same-origin"
        });
        var body = await response.json().catch(function () { return {}; });
        if (!response.ok) {
            throw new Error(body.error || "The reaction request failed.");
        }
        if (!Number.isFinite(Number(body.count))) {
            throw new Error("The reaction response was invalid.");
        }
        return {
            count: Math.max(0, Math.floor(Number(body.count))),
            voted: Boolean(body.voted)
        };
    }

    function setCount(counter, nextCount, animate) {
        var currentCount = Number(counter.textContent);
        if (!animate || !Number.isFinite(currentCount) || currentCount === nextCount) {
            counter.textContent = String(nextCount);
            return;
        }
        if (reduceMotion.matches) {
            counter.textContent = String(nextCount);
            return;
        }

        var jumpToken = String(Number(counter.dataset.jumpToken || "0") + 1);
        counter.dataset.jumpToken = jumpToken;
        var settled = false;
        function settle() {
            if (settled || counter.dataset.jumpToken !== jumpToken) return;
            settled = true;
            counter.textContent = String(nextCount);
            counter.classList.remove("is-jumping");
        }

        counter.classList.add("is-jumping");
        counter.addEventListener("animationend", settle, { once: true });
        window.setTimeout(settle, 400);
    }

    function applyVoteState(widget, button, voted) {
        var isMark = widget.classList.contains("mark-widget");
        widget.classList.toggle("is-voted", voted);
        button.disabled = voted;
        if (isMark) {
            button.hidden = voted;
        } else {
            button.setAttribute(
                "aria-label",
                voted ? "You upvoted this post" : "Upvote this post"
            );
        }
    }

    async function loadReaction(widget) {
        var reactionId = widget.dataset.reactionId;
        var counter = widget.querySelector(".reaction-count");
        var button = widget.querySelector("button");
        var status = widget.querySelector(".reaction-status");

        try {
            var reaction = await requestReaction(reactionId, "GET");
            setCount(counter, reaction.count, false);
            applyVoteState(widget, button, reaction.voted);
            status.textContent = reaction.voted ? "You already reacted here." : "";
        } catch (_) {
            button.disabled = true;
            status.textContent = "The reaction counter is unavailable right now.";
            return;
        }

        button.addEventListener("click", async function () {
            var isMark = widget.classList.contains("mark-widget");
            button.disabled = true;
            if (isMark) button.hidden = true;
            status.textContent = isMark ? "Leaving your mark." : "Saving your upvote.";

            try {
                var reaction = await requestReaction(reactionId, "POST");
                setCount(counter, reaction.count, true);
                applyVoteState(widget, button, true);
                status.textContent = isMark ? "Your mark was left." : "Your upvote was saved.";
            } catch (_) {
                button.hidden = false;
                button.disabled = false;
                status.textContent = "That did not work. Please try again.";
            }
        });
    }

    function initialize() {
        document.querySelectorAll("[data-reaction-id]").forEach(loadReaction);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
