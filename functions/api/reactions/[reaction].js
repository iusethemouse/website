var VISITOR_COOKIE = "hf_reactor";
var VISITOR_ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
var REACTION_ID_RE = /^(?:about|writing--(?:technical|non-fiction|fiction)--[a-z0-9]+(?:-[a-z0-9]+)*)$/;

function jsonResponse(body, status, visitorId, setVisitorCookie) {
    var headers = {
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
        "Content-Type": "application/json; charset=utf-8",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff"
    };
    if (setVisitorCookie) {
        headers["Set-Cookie"] =
            VISITOR_COOKIE + "=" + visitorId +
            "; Path=/; Max-Age=31536000; HttpOnly; Secure; SameSite=Lax";
    }
    return new Response(JSON.stringify(body), { status: status || 200, headers: headers });
}

function readVisitor(request) {
    var cookieHeader = request.headers.get("cookie") || "";
    var visitorId = "";
    cookieHeader.split(";").some(function (part) {
        var pieces = part.trim().split("=");
        if (pieces.shift() !== VISITOR_COOKIE) return false;
        visitorId = pieces.join("=");
        return true;
    });
    if (VISITOR_ID_RE.test(visitorId)) {
        return { id: visitorId, isNew: false };
    }
    return { id: crypto.randomUUID(), isNew: true };
}

function reactionId(context) {
    var value = context.params.reaction;
    if (typeof value !== "string" || !REACTION_ID_RE.test(value)) return "";
    return value;
}

function requireDatabase(context) {
    if (!context.env.REACTIONS_DB) {
        throw new Error("REACTIONS_DB binding is not configured");
    }
    return context.env.REACTIONS_DB;
}

function countStatement(database, reaction, visitorId) {
    return database.prepare(
        "SELECT COUNT(*) AS count, " +
        "EXISTS(SELECT 1 FROM reactions WHERE reaction_id = ?1 AND visitor_id = ?2) AS voted " +
        "FROM reactions WHERE reaction_id = ?1"
    ).bind(reaction, visitorId);
}

function resultBody(result) {
    var row = result && result.results && result.results[0];
    return {
        count: row && Number.isFinite(Number(row.count)) ? Number(row.count) : 0,
        voted: Boolean(row && row.voted)
    };
}

export async function onRequestGet(context) {
    var reaction = reactionId(context);
    if (!reaction) return jsonResponse({ error: "Unknown reaction." }, 404, "", false);

    var visitor = readVisitor(context.request);
    try {
        var result = await countStatement(
            requireDatabase(context),
            reaction,
            visitor.id
        ).all();
        return jsonResponse(resultBody(result), 200, visitor.id, visitor.isNew);
    } catch (error) {
        console.error("Could not load reaction", error);
        return jsonResponse(
            { error: "The reaction could not be loaded." },
            503,
            visitor.id,
            visitor.isNew
        );
    }
}

export async function onRequestPost(context) {
    var reaction = reactionId(context);
    if (!reaction) return jsonResponse({ error: "Unknown reaction." }, 404, "", false);

    var requestOrigin = context.request.headers.get("origin");
    if (!requestOrigin || requestOrigin !== new URL(context.request.url).origin) {
        return jsonResponse({ error: "Cross-origin reactions are not allowed." }, 403, "", false);
    }

    var visitor = readVisitor(context.request);
    try {
        var database = requireDatabase(context);
        var results = await database.batch([
            database.prepare(
                "INSERT OR IGNORE INTO reactions (reaction_id, visitor_id) VALUES (?1, ?2)"
            ).bind(reaction, visitor.id),
            countStatement(database, reaction, visitor.id)
        ]);
        var body = resultBody(results[1]);
        body.created = Boolean(results[0] && results[0].meta && results[0].meta.changes);
        return jsonResponse(body, 200, visitor.id, visitor.isNew);
    } catch (error) {
        console.error("Could not save reaction", error);
        return jsonResponse(
            { error: "The reaction could not be saved." },
            503,
            visitor.id,
            visitor.isNew
        );
    }
}
