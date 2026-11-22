import assert from "node:assert/strict";
import { test } from "node:test";
import { syncBrain } from "./tremplin-brain-sync.mjs";

const cfg = { url: "http://127.0.0.1:8000/mcp", syncToken: "jeton-fictif" };
const folder = { id: "dossier-test", path: "racine-fictive", revision: 3, paused: false };
const change = (sha256) => ({ size: 3, sha256 });
const api = "/api/v1/brain/sync/";
const target = `${api}folders/${folder.id}/`;

function fixture({ complete = true, fail = false } = {}) {
  const serverFiles = new Map([
    ["égal.md", change("identique")],
    ["modifié.md", change("avant")],
    ["supprimé.md", change("retiré")],
  ]);
  const inventory = new Map([
    ["égal.md", change("identique")],
    ["modifié.md", change("après")],
    ["nouveau.md", change("nouveau")],
  ]);
  const edits = [];
  const reports = [];
  const fetcher = async (url, options) => {
    assert.equal(options.headers.Authorization, `Bearer ${cfg.syncToken}`);
    assert.equal(options.redirect, "error");
    const { pathname } = new URL(url);
    if (pathname === `${api}folders`) return Response.json([folder, { ...folder, id: "pause", paused: true }]);
    assert.ok(pathname.startsWith(target));
    assert.equal(options.headers["X-Tremplin-Folder-Revision"], "3");
    if (pathname === `${target}inventory`) return Response.json({
      files: [...serverFiles].map(([path, value]) => ({ path, ...value })),
    });
    if (pathname === `${target}report`) {
      reports.push(JSON.parse(options.body));
      return new Response(null, { status: 204 });
    }
    if (pathname === `${target}files`) {
      const path = options.body.get("path");
      const sha256 = options.body.get("sha256");
      const file = options.body.get("file");
      assert.equal(await file.text(), "abc");
      if (fail && path === "modifié.md") {
        fail = false;
        return new Response(null, { status: 503 });
      }
      serverFiles.set(path, change(sha256));
      edits.push(["save", path]);
      return Response.json({ path, ...change(sha256) });
    }
    assert.equal(pathname, `${target}remove`);
    const { path } = JSON.parse(options.body);
    serverFiles.delete(path);
    edits.push(["remove", path]);
    return new Response(null, { status: 204 });
  };
  return { edits, reports, serverFiles, deps: { fetcher,
    scan: async (root) => {
      assert.equal(root, folder.path);
      return { inventory, complete, ignored: { technical: 2 } };
    },
    read: async (_root, path, expected) => {
      assert.deepEqual(expected, inventory.get(path));
      return Buffer.from("abc");
    },
  } };
}

test("synchronise uniquement les changements d'un dossier actif et conserve un bilan", async () => {
  const { deps, edits, reports } = fixture();
  await syncBrain(cfg, deps);
  assert.deepEqual(edits, [["save", "nouveau.md"], ["save", "modifié.md"], ["remove", "supprimé.md"]]);
  assert.deepEqual(reports.map((report) => report.state), ["syncing", "done"]);
  assert.deepEqual(reports.at(-1), { state: "done", scanned: 3, added: 1, changed: 1, removed: 1,
    ignored: { technical: 2 }, errors: 0 });
});

test("un parcours incomplet laisse les fichiers distants en place", async () => {
  const { deps, edits, reports } = fixture({ complete: false });
  await syncBrain(cfg, deps);
  assert.deepEqual(edits, []);
  assert.equal(reports.at(-1).state, "incomplete");
});

test("une reconnexion reprend les fichiers restants sans recréer ceux déjà présents", async () => {
  const { deps, edits, reports } = fixture({ fail: true });
  await syncBrain(cfg, deps);
  assert.equal(reports.at(-1).state, "incomplete");
  await syncBrain(cfg, deps);
  assert.equal(reports.at(-1).state, "done");
  assert.equal(edits.filter(([, path]) => path === "modifié.md").length, 1);
  assert.equal(edits.filter(([, path]) => path === "nouveau.md").length, 1);
});

test("un fichier inchangé en erreur est renvoyé à cadence bornée jusqu'à son indexation", async () => {
  const { deps, edits, reports, serverFiles } = fixture();
  await syncBrain(cfg, deps);
  edits.length = 0;
  const file = "égal.md";
  const content = serverFiles.get(file);
  let time = 0;
  const run = () => syncBrain(cfg, { ...deps, now: () => time });

  serverFiles.set(file, { ...content, status: "error" });
  await run();
  assert.deepEqual(edits, [["save", file]]);
  assert.equal(reports.at(-1).state, "incomplete");
  assert.equal(reports.at(-1).errors, 1);
  assert.equal(reports.at(-1).changed, 0);

  serverFiles.set(file, { ...content, status: "error" });
  await run();
  assert.equal(edits.length, 1);
  assert.equal(reports.at(-1).state, "incomplete");

  time += 6 * 60_000;
  await run();
  assert.deepEqual(edits, [["save", file], ["save", file]]);

  serverFiles.set(file, { ...content, status: "queued" });
  await run();
  assert.equal(edits.length, 2);
  assert.equal(reports.at(-1).state, "incomplete");

  serverFiles.set(file, { ...content, status: "indexed" });
  await run();
  assert.equal(edits.length, 2);
  assert.equal(reports.at(-1).state, "done");
  assert.equal(reports.at(-1).errors, 0);
});
