import { basename } from "node:path/posix";
import { diffSyncFiles, readSyncFile, scanSyncFiles } from "./tremplin-sync-files.mjs";

const API = "/api/v1/brain/sync/";
const REQUEST_TIMEOUT_MS = 60_000;

function request(cfg, fetcher) {
  return async (path, { revision, ...options } = {}) => {
    const headers = { ...options.headers, Authorization: `Bearer ${cfg.syncToken}` };
    if (revision !== undefined) headers["X-Tremplin-Folder-Revision"] = String(revision);
    const response = await fetcher(new URL(API + path, cfg.url), {
      ...options,
      headers,
      redirect: "error",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    if (!response.ok) throw new Error("brain_sync_http");
    return response.status === 204 ? null : response.json();
  };
}

const postJSON = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function folderRequest(send, folder) {
  const path = `folders/${encodeURIComponent(folder.id)}/`;
  return (endpoint, options) => send(path + endpoint, { ...options, revision: folder.revision });
}

async function upload(send, read, root, entry) {
  const bytes = await read(root, entry.path, { size: entry.size, sha256: entry.sha256 });
  if (bytes === null) throw new Error("brain_sync_file_changed");
  const fields = new FormData();
  fields.append("path", entry.path);
  fields.append("sha256", entry.sha256);
  fields.append("file", new Blob([bytes]), basename(entry.path));
  await send("files", { method: "POST", body: fields });
}

async function sendChanges(send, folder, delta, read, report) {
  for (const entry of delta.added) {
    await upload(send, read, folder.path, entry);
    report.added += 1;
  }
  for (const entry of delta.changed) {
    await upload(send, read, folder.path, entry);
    report.changed += 1;
  }
  for (const path of delta.removed) {
    await send("remove", postJSON({ path }));
    report.removed += 1;
  }
}

async function syncFolder(send, folder, scan, read) {
  const report = { state: "incomplete", scanned: 0, added: 0, changed: 0, removed: 0, ignored: {}, errors: 0 };
  try {
    const scanned = await scan(folder.path);
    report.scanned = scanned.inventory.size;
    report.ignored = scanned.ignored;
    if (scanned.complete) {
      const { files } = await send("inventory");
      const previous = new Map(files.map(({ path, size, sha256 }) => [path, { size, sha256 }]));
      const delta = diffSyncFiles(previous, scanned);
      await send("report", postJSON({ ...report, state: "syncing" }));
      await sendChanges(send, folder, delta, read, report);
      report.state = "done";
    } else {
      report.errors = Math.max(1, (report.ignored.unreadable ?? 0) + (report.ignored.changed ?? 0));
    }
  } catch {
    report.errors += 1;
  }
  try {
    await send("report", postJSON(report));
  } catch {
    report.errors += 1;
  }
  return report;
}

export async function syncBrain(cfg, { fetcher = fetch, scan = scanSyncFiles, read = readSyncFile } = {}) {
  if (!cfg.syncToken) return { folders: 0, errors: 0 };
  const send = request(cfg, fetcher);
  const folders = (await send("folders")).filter((folder) => !folder.paused);
  let errors = 0;
  for (const folder of folders) {
    const report = await syncFolder(folderRequest(send, folder), folder, scan, read);
    errors += report.errors;
  }
  return { folders: folders.length, errors };
}
