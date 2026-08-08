(function () {
    "use strict";

    var schemas = {
        books: [
            { name: "author", label: "author", type: "text", max: 200 },
            { name: "series", label: "series", type: "text", max: 200 },
            { name: "year", label: "publication year", type: "number" }
        ],
        films: [
            { name: "director", label: "director", type: "text", max: 200 },
            { name: "country", label: "country", type: "text", max: 100 },
            { name: "year", label: "release year", type: "number" }
        ],
        tv: [
            { name: "creator", label: "creator", type: "text", max: 200 },
            { name: "year_start", label: "first year", type: "number" },
            { name: "year_end", label: "final year", type: "number" },
            { name: "seasons", label: "seasons", type: "number", min: 1, max: 999 }
        ],
        games: [
            { name: "studio", label: "studio", type: "text", max: 200 },
            { name: "year", label: "release year", type: "number" },
            { name: "genre", label: "genre", type: "text", max: 100 }
        ]
    };

    var form = document.getElementById("collection-form");
    var category = document.getElementById("category");
    var fields = document.getElementById("category-fields");
    var title = document.getElementById("title");
    var slug = document.getElementById("slug");
    var cover = document.getElementById("cover");
    var preview = document.getElementById("cover-preview");
    var status = document.getElementById("form-status");
    var submit = form.querySelector("button[type=submit]");
    var slugWasEdited = false;
    var previewUrl = "";

    function slugify(value) {
        return value
            .normalize("NFKD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .slice(0, 120)
            .replace(/-+$/g, "");
    }

    function renderCategoryFields() {
        fields.replaceChildren();
        schemas[category.value].forEach(function (definition) {
            var label = document.createElement("label");
            label.append(document.createTextNode(definition.label + " "));

            var optional = document.createElement("span");
            optional.className = "optional";
            optional.textContent = "optional";
            label.append(optional);

            var input = document.createElement("input");
            input.name = definition.name;
            input.type = definition.type;
            if (definition.type === "number") {
                input.min = definition.min || 1000;
                input.max = definition.max || 2999;
                input.inputMode = "numeric";
            } else if (definition.max) {
                input.maxLength = definition.max;
            }
            label.append(input);
            fields.append(label);
        });
        history.replaceState(null, "", "?category=" + encodeURIComponent(category.value));
    }

    function showStatus(message, kind, link) {
        status.className = "form-status " + (kind || "");
        status.replaceChildren(document.createTextNode(message));
        if (link) {
            status.append(document.createTextNode(" "));
            var anchor = document.createElement("a");
            anchor.href = link;
            anchor.textContent = "view commit";
            anchor.target = "_blank";
            anchor.rel = "noreferrer";
            status.append(anchor);
        }
    }

    category.addEventListener("change", renderCategoryFields);
    title.addEventListener("input", function () {
        if (!slugWasEdited) slug.value = slugify(title.value);
    });
    slug.addEventListener("input", function () {
        slugWasEdited = slug.value.length > 0;
    });

    cover.addEventListener("change", function () {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = "";
        preview.hidden = true;
        var file = cover.files[0];
        if (!file) return;
        if (file.size > 8 * 1024 * 1024) {
            cover.value = "";
            showStatus("That image is larger than 8 MB.", "error");
            return;
        }
        previewUrl = URL.createObjectURL(file);
        preview.src = previewUrl;
        preview.hidden = false;
    });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        submit.disabled = true;
        showStatus("committing…", "working");

        try {
            var response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: { Accept: "application/json" }
            });
            var result = await response.json().catch(function () {
                return { error: "The server returned an unreadable response." };
            });
            if (!response.ok) throw new Error(result.error || "Submission failed.");

            showStatus("Entry committed. Cloudflare is building it now.", "success", result.commit_url);
            var selectedCategory = category.value;
            form.reset();
            category.value = selectedCategory;
            slugWasEdited = false;
            renderCategoryFields();
            preview.hidden = true;
        } catch (error) {
            showStatus(error.message || "Submission failed.", "error");
        } finally {
            submit.disabled = false;
        }
    });

    var requestedCategory = new URLSearchParams(location.search).get("category");
    if (requestedCategory && schemas[requestedCategory]) category.value = requestedCategory;
    renderCategoryFields();
})();
