import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import { link, mkdir, mkdtemp, realpath, rm, symlink, truncate, writeFile } from "node:fs/promises";
import { syncBuiltinESMExports } from "node:module";
import { tmpdir } from "node:os";
import { isAbsolute, join, relative, sep } from "node:path";
import { test } from "node:test";
import * as scanner from "./tremplin-sync-files.mjs";

const { diffSyncFiles, scanSyncFiles } = scanner;

async function fixture(t) {
  const base = await realpath(tmpdir());
  const outside = await mkdtemp(join(base, "tremplin-sync-fictif-"));
  t.after(async () => {
    const target = await realpath(outside);
    const within = relative(base, target);
    assert.ok(within.startsWith("tremplin-sync-fictif-") && !within.includes(sep) && !isAbsolute(within));
    await rm(target, { recursive: true, force: true });
  });
  const root = join(outside, "coffre-fictif");
  await mkdir(root);
  return { outside, root };
}

function fingerprint(text) {
  return { size: Buffer.byteLength(text), sha256: createHash("sha256").update(text).digest("hex") };
}

test("skips excluded subtrees and file extensions using the configured rules", async (t) => {
  const { root } = await fixture(t);
  await mkdir(join(root, "Archives"));
  await writeFile(join(root, "Archives", "ancienne.md"), "Fichier fictif");
  await writeFile(join(root, "PJ.TXT"), "Fichier fictif");
  await writeFile(join(root, "note.md"), "Fichier fictif");
  const scan = await scanSyncFiles(root, {
    excluded_directories: ["archives"], excluded_extensions: [".txt"],
  });
  assert.deepEqual([...scan.inventory.keys()], ["note.md"]);
  assert.equal(scan.ignored.excluded, 2);
});

test("orders permitted documents by POSIX path and reports why others were skipped", async (t) => {
  const { root } = await fixture(t);
  await mkdir(join(root, "Pages"));
  for (const dir of [".obsidian", ".git", ".venv", "node_modules"]) {
    await mkdir(join(root, dir));
    await writeFile(join(root, dir, "hors-inventaire.md"), "Texte fictif ignoré.");
  }
  const files = {
    "zzz.TXT": "Texte fictif avec un accent : é.",
    "Pages/article.PDF": "%PDF-1.7 exemple",
    "Pages/document.docx": "PK\u0003\u0004en-tête fictif",
    "Pages/modele.py": "answer = 42\n",
    "Pages/note.md": "\ufeff# Note fictive\n",
    "Pages/nouveau.ts": "const answer = 42;\n",
    "Pages/notes.ipynb": "{\"cells\":[]}",
    "Pages/script.js": "const answer = 42;\n",
  };
  for (const [file, text] of Object.entries(files)) await writeFile(join(root, file), text);
  await writeFile(join(root, "renomme.md"), Buffer.from([0xf0, 0x28, 0x8c, 0x28]));
  await writeFile(join(root, "avec-nul.py"), Buffer.from([0x61, 0x00, 0x62]));
  await writeFile(join(root, "renomme.pdf"), "Texte sans signature PDF.");
  await writeFile(join(root, "renomme.docx"), "Texte sans signature ZIP.");
  for (const name of ["photo.png", "enregistrement.mp3", "video.mp4", "binaire.exe"]) {
    await writeFile(join(root, name), "Fichier fictif hors périmètre.");
  }

  const { inventory, ignored, complete } = await scanSyncFiles(root);

  assert.ok(complete);
  assert.deepEqual([...inventory], Object.keys(files).sort().map((path) => [path, fingerprint(files[path])]));
  assert.deepEqual(
    { technical: ignored.technical, extension: ignored.extension, binary: ignored.binary },
    { technical: 4, extension: 4, binary: 4 },
  );
});

test("accepts twenty MiB exactly without reading larger files", async (t) => {
  const { root } = await fixture(t);
  const cap = 20 * 1024 * 1024;
  await writeFile(join(root, "limite.txt"), Buffer.alloc(cap, 0x61));
  const larger = join(root, "depasse.txt");
  await writeFile(larger, "");
  await truncate(larger, cap + 1);

  const { inventory, ignored, complete } = await scanSyncFiles(root);

  assert.ok(complete);
  assert.deepEqual([...inventory.keys()], ["limite.txt"]);
  assert.equal(inventory.get("limite.txt").size, cap);
  assert.equal(ignored.tooLarge, 1);
});

test("skips directory links and linked files and refuses an aliased root", async (t) => {
  const { root, outside } = await fixture(t);
  const privateDir = join(outside, "hors-racine");
  await mkdir(privateDir);
  const privateFile = join(privateDir, "faux-secret.md");
  await writeFile(privateFile, "Un contenu de test privé.");
  const junctionType = process.platform === "win32" ? "junction" : "dir";
  await symlink(privateDir, join(root, "jonction"), junctionType);
  await link(privateFile, join(root, "lien-physique.md"));
  let linkCount = 2;
  try {
    await symlink(privateFile, join(root, "lien-symbolique.md"), "file");
    linkCount += 1;
  } catch (err) {
    if (process.platform !== "win32" || err.code !== "EPERM") throw err;
  }
  await writeFile(join(root, "note.md"), "Note laissée dans le coffre.");

  const { inventory, ignored, complete } = await scanSyncFiles(root);

  assert.ok(complete);
  assert.deepEqual([...inventory.keys()], ["note.md"]);
  assert.equal(ignored.link, linkCount);
  await assert.rejects(scanSyncFiles(join(root, "jonction")), { code: "sync_root_link" });
  await mkdir(join(privateDir, "interieur"));
  await assert.rejects(scanSyncFiles(join(root, "jonction", "interieur")), { code: "sync_root_link" });
});

test("detects additions, same-size edits and removals without re-sending unchanged files", async (t) => {
  const { root } = await fixture(t);
  for (const path of ["modifie.md", "retire.txt", "stable.md"]) await writeFile(join(root, path), "a");
  const previous = (await scanSyncFiles(root)).inventory;
  await writeFile(join(root, "modifie.md"), "b");
  await writeFile(join(root, "ajoute.md"), "c");
  await rm(join(root, "retire.txt"));

  const changes = diffSyncFiles(previous, await scanSyncFiles(root));

  assert.deepEqual(changes, {
    added: [{ path: "ajoute.md", ...fingerprint("c") }],
    changed: [{ path: "modifie.md", ...fingerprint("b") }],
    removed: ["retire.txt"],
    unchanged: 1,
  });
});

test("refuses unavailable roots and incomplete diffs without exposing local names", async (t) => {
  const { root } = await fixture(t);
  await assert.rejects(scanSyncFiles("chemin-relatif"), { code: "sync_root_invalid" });
  await assert.rejects(scanSyncFiles(join(root, "faux-secret")), (error) => {
    assert.equal(error.code, "sync_root_unavailable");
    assert.doesNotMatch(error.message, /faux-secret|coffre-fictif/);
    return true;
  });
  const previous = new Map([["ancienne-note.md", fingerprint("a")]]);
  assert.throws(() => diffSyncFiles(previous, { inventory: new Map(), complete: false }), {
    code: "sync_scan_incomplete",
  });
});

test("a directory changed while listing is incomplete and can be scanned again", async (t) => {
  const { root } = await fixture(t);
  await writeFile(join(root, "stable.md"), "a");
  const previous = (await scanSyncFiles(root)).inventory;
  const readDirectory = fs.readdir;
  const mock = t.mock.method(fs, "readdir", async (path) => {
    const names = await readDirectory(path);
    if (path === root) {
      await writeFile(join(root, "ajoute.md"), "b");
      const modified = new Date("2026-11-01T12:00:00Z");
      await fs.utimes(root, modified, modified);
    }
    return names;
  });
  syncBuiltinESMExports();
  try {
    const racing = await scanSyncFiles(root);
    assert.equal(racing.complete, false);
    assert.equal(racing.ignored.changed, 1);
    assert.throws(() => diffSyncFiles(previous, racing), { code: "sync_scan_incomplete" });
  } finally {
    mock.mock.restore();
    syncBuiltinESMExports();
  }
  const next = diffSyncFiles(previous, await scanSyncFiles(root));
  assert.deepEqual(next.added, [{ path: "ajoute.md", ...fingerprint("b") }]);
  assert.deepEqual(next.removed, []);
});

test("reads the exact scanned bytes for transfer and rejects stale or escaped paths", async (t) => {
  const { root, outside } = await fixture(t);
  const directory = join(root, "notes");
  await mkdir(directory);
  const content = Buffer.from("texte fictif en UTF-8 : é");
  await writeFile(join(directory, "note.md"), content);
  await writeFile(join(outside, "hors-racine.md"), content);
  const scan = await scanSyncFiles(root);
  const expected = scan.inventory.get("notes/note.md");

  assert.equal(typeof scanner.readSyncFile, "function");
  assert.deepEqual(await scanner.readSyncFile(root, "notes/note.md", expected), content);
  assert.equal(await scanner.readSyncFile(root, "../hors-racine.md", expected), null);
  assert.equal(await scanner.readSyncFile(root, "notes\\note.md", expected), null);
  const junctionType = process.platform === "win32" ? "junction" : "dir";
  await symlink(outside, join(root, "jonction"), junctionType);
  assert.equal(await scanner.readSyncFile(root, "jonction/hors-racine.md", expected), null);
  await writeFile(join(directory, "note.md"), Buffer.alloc(content.length, 0x78));
  assert.equal(await scanner.readSyncFile(root, "notes/note.md", expected), null);
});
