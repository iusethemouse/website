import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
    new URL("../functions/api/reactions/[reaction].js", import.meta.url),
    "utf8"
);
const moduleUrl = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const { onRequestGet, onRequestPost } = await import(moduleUrl);

class FakeStatement {
    constructor(database, sql) {
        this.database = database;
        this.sql = sql;
        this.values = [];
    }

    bind(...values) {
        this.values = values;
        return this;
    }

    execute() {
        const [reaction, visitor] = this.values;
        const key = reaction + "\n" + visitor;
        if (this.sql.startsWith("INSERT")) {
            const previousSize = this.database.rows.size;
            this.database.rows.add(key);
            return {
                results: [],
                meta: { changes: this.database.rows.size === previousSize ? 0 : 1 }
            };
        }

        const count = Array.from(this.database.rows).filter(function (row) {
            return row.startsWith(reaction + "\n");
        }).length;
        return {
            results: [{ count: count, voted: this.database.rows.has(key) ? 1 : 0 }],
            meta: { changes: 0 }
        };
    }

    async all() {
        return this.execute();
    }
}

class FakeDatabase {
    constructor() {
        this.rows = new Set();
    }

    prepare(sql) {
        return new FakeStatement(this, sql);
    }

    async batch(statements) {
        return statements.map(function (statement) {
            return statement.execute();
        });
    }
}

function context(database, method, reaction, headers = {}) {
    return {
        env: { REACTIONS_DB: database },
        params: { reaction: reaction },
        request: new Request("https://humanoid-factoid.com/api/reactions/" + reaction, {
            method: method,
            headers: headers
        })
    };
}

test("a browser can leave one mark and duplicate requests remain idempotent", async function () {
    const database = new FakeDatabase();
    const firstGet = await onRequestGet(context(database, "GET", "about"));
    assert.equal(firstGet.status, 200);
    assert.deepEqual(await firstGet.json(), { count: 0, voted: false });

    const cookie = firstGet.headers.get("set-cookie").split(";", 1)[0];
    const postHeaders = {
        Cookie: cookie,
        Origin: "https://humanoid-factoid.com"
    };
    const firstPost = await onRequestPost(
        context(database, "POST", "about", postHeaders)
    );
    assert.equal(firstPost.status, 200);
    assert.deepEqual(await firstPost.json(), { count: 1, voted: true, created: true });

    const duplicatePost = await onRequestPost(
        context(database, "POST", "about", postHeaders)
    );
    assert.deepEqual(await duplicatePost.json(), {
        count: 1,
        voted: true,
        created: false
    });

    const returningGet = await onRequestGet(
        context(database, "GET", "about", { Cookie: cookie })
    );
    assert.deepEqual(await returningGet.json(), { count: 1, voted: true });
});

test("another browser sees the shared count but has not voted", async function () {
    const database = new FakeDatabase();
    await onRequestPost(
        context(database, "POST", "writing--fiction--2014-sleepless-mind", {
            Origin: "https://humanoid-factoid.com"
        })
    );

    const response = await onRequestGet(
        context(database, "GET", "writing--fiction--2014-sleepless-mind")
    );
    assert.deepEqual(await response.json(), { count: 1, voted: false });
});

test("cross-origin and unknown reactions are rejected", async function () {
    const database = new FakeDatabase();
    const crossOrigin = await onRequestPost(
        context(database, "POST", "about", { Origin: "https://example.com" })
    );
    assert.equal(crossOrigin.status, 403);
    assert.equal(database.rows.size, 0);

    const unknown = await onRequestGet(context(database, "GET", "made-up-post"));
    assert.equal(unknown.status, 404);
});
