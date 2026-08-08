var jwksCache = { teamDomain: "", expiresAt: 0, keys: [] };

var CATEGORY_FIELDS = {
    books: ["author", "series", "year"],
    films: ["director", "country", "year"],
    tv: ["creator", "year_start", "year_end", "seasons"],
    games: ["studio", "year", "genre"]
};

var FIELD_LIMITS = {
    title: 200,
    author: 200,
    series: 200,
    director: 200,
    country: 100,
    creator: 200,
    studio: 200,
    genre: 100,
    year: 4,
    year_start: 4,
    year_end: 4,
    seasons: 3,
    date: 10,
    slug: 120
};

class RequestError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status || 400;
    }
}

class ConfigurationError extends Error {}

class GitHubError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

function jsonResponse(body, status) {
    return Response.json(body, {
        status: status || 200,
        headers: {
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY"
        }
    });
}

function decodeBase64Url(value) {
    var base64 = value.replace(/-/g, "+").replace(/_/g, "/");
    base64 += "=".repeat((4 - (base64.length % 4)) % 4);
    var decoded = atob(base64);
    var bytes = new Uint8Array(decoded.length);
    for (var index = 0; index < decoded.length; index += 1) {
        bytes[index] = decoded.charCodeAt(index);
    }
    return bytes;
}

function decodeJwtJson(segment) {
    try {
        return JSON.parse(new TextDecoder().decode(decodeBase64Url(segment)));
    } catch (_) {
        throw new RequestError("Invalid authentication token.", 403);
    }
}

function normalizeTeamDomain(value) {
    if (!value) throw new ConfigurationError("TEAM_DOMAIN is not configured");
    var url;
    try {
        url = new URL(value);
    } catch (_) {
        throw new ConfigurationError("TEAM_DOMAIN must be a full HTTPS URL");
    }
    if (url.protocol !== "https:" || url.pathname !== "/") {
        throw new ConfigurationError("TEAM_DOMAIN must be an HTTPS origin without a path");
    }
    return url.origin;
}

async function getSigningKey(teamDomain, keyId, forceRefresh) {
    var now = Date.now();
    if (
        forceRefresh ||
        jwksCache.teamDomain !== teamDomain ||
        jwksCache.expiresAt <= now
    ) {
        var response = await fetch(teamDomain + "/cdn-cgi/access/certs", {
            headers: { Accept: "application/json" }
        });
        if (!response.ok) throw new RequestError("Could not verify authentication.", 503);
        var body = await response.json();
        jwksCache = {
            teamDomain: teamDomain,
            expiresAt: now + 60 * 60 * 1000,
            keys: Array.isArray(body.keys) ? body.keys : []
        };
    }
    return jwksCache.keys.find(function (key) {
        return key.kid === keyId;
    });
}

async function authenticate(request, env) {
    if (!env.POLICY_AUD || !env.ADMIN_EMAIL) {
        throw new ConfigurationError("Access environment variables are incomplete");
    }

    var teamDomain = normalizeTeamDomain(env.TEAM_DOMAIN);
    var token = request.headers.get("cf-access-jwt-assertion") || "";
    if (!token || token.length > 12000) {
        throw new RequestError("Authentication is required.", 403);
    }

    var segments = token.split(".");
    if (segments.length !== 3) throw new RequestError("Invalid authentication token.", 403);
    var header = decodeJwtJson(segments[0]);
    var payload = decodeJwtJson(segments[1]);
    if (header.alg !== "RS256" || typeof header.kid !== "string") {
        throw new RequestError("Invalid authentication token.", 403);
    }

    var jwk = await getSigningKey(teamDomain, header.kid, false);
    if (!jwk) jwk = await getSigningKey(teamDomain, header.kid, true);
    if (!jwk) throw new RequestError("Authentication signing key was not found.", 403);

    var key = await crypto.subtle.importKey(
        "jwk",
        jwk,
        { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
        false,
        ["verify"]
    );
    var validSignature = await crypto.subtle.verify(
        "RSASSA-PKCS1-v1_5",
        key,
        decodeBase64Url(segments[2]),
        new TextEncoder().encode(segments[0] + "." + segments[1])
    );

    var now = Math.floor(Date.now() / 1000);
    var audiences = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    var validClaims =
        validSignature &&
        payload.iss === teamDomain &&
        audiences.indexOf(env.POLICY_AUD) !== -1 &&
        typeof payload.exp === "number" &&
        payload.exp > now - 30 &&
        (typeof payload.nbf !== "number" || payload.nbf <= now + 30) &&
        typeof payload.email === "string" &&
        payload.email.toLowerCase() === env.ADMIN_EMAIL.trim().toLowerCase();

    if (!validClaims) throw new RequestError("You are not allowed to submit entries.", 403);
    return payload;
}

function textField(form, name, required) {
    var value = form.get(name);
    if (typeof value !== "string") value = "";
    value = value.trim();
    if (required && !value) throw new RequestError(name + " is required.");
    if (value.length > FIELD_LIMITS[name]) throw new RequestError(name + " is too long.");
    if (/[\u0000-\u001f\u007f]/.test(value)) {
        throw new RequestError(name + " contains an unsupported control character.");
    }
    return value;
}

function validateDate(value) {
    var match = /^(19|20)\d{2}(?:-(0[1-9]|1[0-2])(?:-(0[1-9]|[12]\d|3[01]))?)?$/.exec(value);
    if (!match) throw new RequestError("date must be YYYY, YYYY-MM, or YYYY-MM-DD.");
    if (match[3]) {
        var parts = value.split("-").map(Number);
        var candidate = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
        if (
            candidate.getUTCFullYear() !== parts[0] ||
            candidate.getUTCMonth() !== parts[1] - 1 ||
            candidate.getUTCDate() !== parts[2]
        ) {
            throw new RequestError("date is not a real calendar date.");
        }
    }
}

function validateMetadata(fields) {
    ["year", "year_start", "year_end"].forEach(function (name) {
        if (fields[name] && !/^\d{4}$/.test(fields[name])) {
            throw new RequestError(name + " must be a four-digit year.");
        }
    });
    if (fields.seasons && (!/^\d{1,3}$/.test(fields.seasons) || Number(fields.seasons) < 1)) {
        throw new RequestError("seasons must be a positive number.");
    }
    if (fields.year_end && !fields.year_start) {
        throw new RequestError("year_start is required when year_end is set.");
    }
}

function detectImage(bytes) {
    if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
        return "jpg";
    }
    if (
        bytes.length >= 8 &&
        bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47 &&
        bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a
    ) {
        return "png";
    }
    if (
        bytes.length >= 12 &&
        String.fromCharCode.apply(null, bytes.slice(0, 4)) === "RIFF" &&
        String.fromCharCode.apply(null, bytes.slice(8, 12)) === "WEBP"
    ) {
        return "webp";
    }
    throw new RequestError("cover must be a valid JPEG, PNG, or WebP image.");
}

function bytesToBase64(bytes) {
    var binary = "";
    var chunkSize = 0x8000;
    for (var offset = 0; offset < bytes.length; offset += chunkSize) {
        binary += String.fromCharCode.apply(null, bytes.subarray(offset, offset + chunkSize));
    }
    return btoa(binary);
}

function repoSettings(env) {
    var settings = {
        owner: env.GITHUB_OWNER || "iusethemouse",
        repo: env.GITHUB_REPO || "website",
        branch: env.GITHUB_BRANCH || "main",
        token: env.GITHUB_TOKEN || ""
    };
    if (!settings.token) throw new ConfigurationError("GITHUB_TOKEN is not configured");
    if (!/^[A-Za-z0-9_.-]+$/.test(settings.owner) || !/^[A-Za-z0-9_.-]+$/.test(settings.repo)) {
        throw new ConfigurationError("GitHub owner or repository name is invalid");
    }
    if (!/^[A-Za-z0-9._/-]+$/.test(settings.branch)) {
        throw new ConfigurationError("GitHub branch name is invalid");
    }
    return settings;
}

async function githubRequest(settings, method, path, body) {
    var response = await fetch(
        "https://api.github.com/repos/" + encodeURIComponent(settings.owner) + "/" +
            encodeURIComponent(settings.repo) + path,
        {
            method: method,
            headers: {
                Accept: "application/vnd.github+json",
                Authorization: "Bearer " + settings.token,
                "Content-Type": "application/json",
                "User-Agent": "humanoid-factoid-collection-form",
                "X-GitHub-Api-Version": "2022-11-28"
            },
            body: body === undefined ? undefined : JSON.stringify(body)
        }
    );
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
        throw new GitHubError(data.message || "GitHub rejected the request.", response.status);
    }
    return data;
}

async function githubPathExists(settings, path) {
    try {
        await githubRequest(
            settings,
            "GET",
            "/contents/" + path.split("/").map(encodeURIComponent).join("/") +
                "?ref=" + encodeURIComponent(settings.branch)
        );
        return true;
    } catch (error) {
        if (error instanceof GitHubError && error.status === 404) return false;
        throw error;
    }
}

async function commitFiles(settings, files, message) {
    var refPath = "/git/ref/heads/" + settings.branch.split("/").map(encodeURIComponent).join("/");
    var head = await githubRequest(settings, "GET", refPath);
    var parentSha = head.object.sha;
    var parent = await githubRequest(settings, "GET", "/git/commits/" + parentSha);

    var tree = [];
    for (var file of files) {
        var blob = await githubRequest(settings, "POST", "/git/blobs", {
            content: file.encoding === "base64" ? file.content : file.content,
            encoding: file.encoding
        });
        tree.push({ path: file.path, mode: "100644", type: "blob", sha: blob.sha });
    }

    var newTree = await githubRequest(settings, "POST", "/git/trees", {
        base_tree: parent.tree.sha,
        tree: tree
    });
    var commit = await githubRequest(settings, "POST", "/git/commits", {
        message: message,
        tree: newTree.sha,
        parents: [parentSha]
    });
    await githubRequest(
        settings,
        "PATCH",
        "/git/refs/heads/" + settings.branch.split("/").map(encodeURIComponent).join("/"),
        { sha: commit.sha, force: false }
    );
    return commit.sha;
}

async function handleSubmission(request, env) {
    await authenticate(request, env);

    var origin = request.headers.get("origin");
    if (!origin || origin !== new URL(request.url).origin) {
        throw new RequestError("Cross-origin submissions are not allowed.", 403);
    }
    var length = Number(request.headers.get("content-length") || 0);
    if (length > 10 * 1024 * 1024) throw new RequestError("Submission is too large.", 413);
    if (!(request.headers.get("content-type") || "").toLowerCase().startsWith("multipart/form-data")) {
        throw new RequestError("Expected a form submission.", 415);
    }

    var form;
    try {
        form = await request.formData();
    } catch (_) {
        throw new RequestError("The submitted form could not be read.");
    }

    var category = textField(form, "category", true);
    if (!Object.prototype.hasOwnProperty.call(CATEGORY_FIELDS, category)) {
        throw new RequestError("Unknown collection category.");
    }
    var title = textField(form, "title", true);
    var slug = textField(form, "slug", true);
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
        throw new RequestError("slug must contain lowercase letters, numbers, and hyphens only.");
    }
    var experienced = textField(form, "date", true);
    validateDate(experienced);

    var metadata = { title: title };
    CATEGORY_FIELDS[category].forEach(function (name) {
        var value = textField(form, name, false);
        if (value) metadata[name] = value;
    });
    metadata.date = experienced;
    validateMetadata(metadata);

    var cover = form.get("cover");
    var coverBytes = null;
    var coverExtension = "";
    if (cover && typeof cover === "object" && typeof cover.arrayBuffer === "function" && cover.size) {
        if (cover.size > 8 * 1024 * 1024) throw new RequestError("cover is larger than 8 MB.", 413);
        coverBytes = new Uint8Array(await cover.arrayBuffer());
        coverExtension = detectImage(coverBytes);
        metadata.cover = slug + "." + coverExtension;
    }

    var blurbValue = form.get("blurb");
    var blurb = typeof blurbValue === "string" ? blurbValue.trim() : "";
    if (blurb.length > 20000) throw new RequestError("blurb is too long.");
    if (blurb.indexOf("\u0000") !== -1) throw new RequestError("blurb contains an invalid character.");

    var orderedFields = ["title"].concat(CATEGORY_FIELDS[category], ["date", "cover"]);
    var frontmatter = orderedFields
        .filter(function (name) { return metadata[name]; })
        .map(function (name) { return name + ": " + metadata[name]; })
        .join("\n");
    var markdown = "---\n" + frontmatter + "\n---\n" + (blurb ? blurb + "\n" : "");

    var settings = repoSettings(env);
    var markdownPath = "content/collections/" + category + "/" + slug + ".md";
    if (await githubPathExists(settings, markdownPath)) {
        throw new RequestError("An entry with that slug already exists.", 409);
    }

    var files = [{ path: markdownPath, content: markdown, encoding: "utf-8" }];
    if (coverBytes) {
        var coverPath = "static/covers/" + category + "/" + metadata.cover;
        if (await githubPathExists(settings, coverPath)) {
            throw new RequestError("A cover with that filename already exists.", 409);
        }
        files.push({ path: coverPath, content: bytesToBase64(coverBytes), encoding: "base64" });
    }

    var sha = await commitFiles(settings, files, "Add " + title + " to " + category);
    return {
        commit: sha,
        commit_url: "https://github.com/" + settings.owner + "/" + settings.repo + "/commit/" + sha
    };
}

export async function onRequest(context) {
    if (context.request.method !== "POST") {
        return jsonResponse({ error: "Method not allowed." }, 405);
    }
    try {
        var result = await handleSubmission(context.request, context.env);
        return jsonResponse(result, 201);
    } catch (error) {
        if (error instanceof RequestError) {
            return jsonResponse({ error: error.message }, error.status);
        }
        if (error instanceof ConfigurationError) {
            console.error(error.message);
            return jsonResponse({ error: "The submission service is not configured yet." }, 503);
        }
        if (error instanceof GitHubError) {
            console.error("GitHub API error", error.status, error.message);
            var status = error.status === 409 || error.status === 422 ? 409 : 502;
            var message = status === 409
                ? "The repository changed while submitting. Please try again."
                : "GitHub could not accept the entry. Please try again.";
            return jsonResponse({ error: message }, status);
        }
        console.error("Unexpected collection submission error", error);
        return jsonResponse({ error: "Unexpected submission error." }, 500);
    }
}
