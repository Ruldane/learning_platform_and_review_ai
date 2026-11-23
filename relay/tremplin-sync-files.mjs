// Inventaire local Cerveau. Les erreurs et le bilan ne portent ni noms ni textes des notes.
import { createHash } from "node:crypto";
import { constants } from "node:fs";
import { lstat, open, readdir, realpath } from "node:fs/promises";
import { basename, extname, isAbsolute, join, parse, relative, resolve, sep } from "node:path";

export const MAX_SYNC_FILE_BYTES = 20 * 1024 * 1024;
export const SYNC_TEXT_EXTENSIONS = Object.freeze([
  ".md", ".markdown", ".txt", ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs",
  ".ts", ".tsx", ".mts", ".cts", ".ipynb", ".json", ".yaml", ".yml", ".toml",
  ".sql", ".sh", ".ps1", ".html", ".css", ".java", ".kt", ".rb", ".go", ".rs",
  ".c", ".h", ".cpp", ".hpp", ".cs", ".r", ".lua", ".php", ".swift", ".scala",
  ".vue", ".svelte", ".xml", ".rst", ".adoc",
]);

const TEXT = new Set(SYNC_TEXT_EXTENSIONS);
const DOCUMENT_SIGNATURES = new Map([
  [".pdf", Buffer.from("%PDF-")],
  [".docx", Buffer.from([0x50, 0x4b, 0x03, 0x04])],
]);
const TECHNICAL = new Set([
  ".obsidian", ".git", ".hg", ".svn", "node_modules", ".pnpm-store", ".venv", "venv",
  "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints",
  ".idea", ".vscode", ".tox", ".nox", ".next",
]);
const STAT_OPTIONS = { bigint: true };
const READ_FLAGS = constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0) | (constants.O_NONBLOCK ?? 0);
const MAX_SIZE = BigInt(MAX_SYNC_FILE_BYTES);
const CHUNK_SIZE = 64 * 1024;

const SCAN_MESSAGES = {
  sync_root_invalid: "Le dossier synchronisé doit avoir un chemin local absolu.",
  sync_root_technical: "Ce dossier technique est exclu de la synchronisation.",
  sync_root_unavailable: "Le dossier synchronisé est indisponible.",
  sync_root_link: "Le dossier synchronisé passe par un lien ou une jonction.",
  sync_scan_incomplete: "Le parcours est incomplet. L'inventaire précédent reste en vigueur.",
};

class ScanError extends Error {
  constructor(code) {
    super(SCAN_MESSAGES[code]);
    this.code = code;
  }
}

class EntryChanged extends Error {}

function validComponent(name) {
  return !!name && name !== "." && name !== ".." && !/[\\:\u0000-\u001f\u007f]/u.test(name);
}

function rootPath(path) {
  if (typeof path !== "string" || !isAbsolute(path) || path.includes("\0")) {
    throw new ScanError("sync_root_invalid");
  }
  if (process.platform === "win32" && !/^[A-Za-z]:[\\/]/u.test(path)) {
    throw new ScanError("sync_root_invalid");
  }
  const root = resolve(path);
  if (TECHNICAL.has(basename(root).toLowerCase())) throw new ScanError("sync_root_technical");
  return root;
}

async function rootDirectories(path) {
  const root = rootPath(path);
  const anchor = parse(root).root;
  const paths = [anchor];
  for (const part of root.slice(anchor.length).split(sep).filter(Boolean)) {
    paths.push(join(paths.at(-1), part));
  }
  const directories = [];
  try {
    for (const absolute of paths) {
      const stat = await lstat(absolute, STAT_OPTIONS);
      if (stat.isSymbolicLink()) throw new ScanError("sync_root_link");
      if (!stat.isDirectory()) throw new ScanError("sync_root_unavailable");
      directories.push({ absolute, stat });
    }
    if (relative(root, await realpath(root)) !== "") throw new ScanError("sync_root_link");
  } catch (error) {
    if (error instanceof ScanError) throw error;
    throw new ScanError("sync_root_unavailable");
  }
  return directories;
}

function sameObject(first, second) {
  return first.dev === second.dev && first.ino === second.ino;
}

async function checkDirectories(directories) {
  let current;
  for (const { absolute, stat } of directories) {
    current = await lstat(absolute, STAT_OPTIONS);
    if (!current.isDirectory() || !sameObject(stat, current)) throw new EntryChanged();
  }
  const { absolute } = directories.at(-1);
  if (relative(absolute, await realpath(absolute)) !== "") throw new EntryChanged();
  return current;
}

function checkTimestamps(before, after) {
  if (before.mtimeNs !== after.mtimeNs || before.ctimeNs !== after.ctimeNs) throw new EntryChanged();
}

function checkFile(stat, current) {
  if (!current.isFile() || current.nlink !== 1n || !sameObject(stat, current) ||
      stat.size !== current.size) {
    throw new EntryChanged();
  }
  checkTimestamps(stat, current);
}

function textChunk(decoder, chunk) {
  if (chunk.includes(0)) return false;
  try {
    decoder.decode(chunk, { stream: true });
    return true;
  } catch {
    return false;
  }
}

async function digest(file, size, signature, capture) {
  if (signature && size < signature.length) return null;
  const hash = createHash("sha256");
  const decoder = signature ? null : new TextDecoder("utf-8", { fatal: true });
  const head = signature ? Buffer.alloc(signature.length) : null;
  const buffer = Buffer.alloc(capture ? size : Math.min(size, CHUNK_SIZE));
  let position = 0;
  while (position < size) {
    const length = Math.min(CHUNK_SIZE, size - position);
    const offset = capture ? position : 0;
    const { bytesRead } = await file.read(buffer, offset, length, position);
    if (bytesRead === 0) throw new EntryChanged();
    const chunk = buffer.subarray(offset, offset + bytesRead);
    if (decoder && !textChunk(decoder, chunk)) return null;
    if (head && position < head.length) {
      chunk.copy(head, position, 0, head.length - position);
      if (position + bytesRead >= head.length && !head.equals(signature)) return null;
    }
    hash.update(chunk);
    position += bytesRead;
  }
  try {
    decoder?.decode();
  } catch {
    return null;
  }
  const info = { size, sha256: hash.digest("hex") };
  return capture ? { ...info, bytes: buffer } : info;
}

async function fingerprint(directories, absolute, stat, signature, capture = false) {
  await checkDirectories(directories);
  checkFile(stat, await lstat(absolute, STAT_OPTIONS));
  if (relative(absolute, await realpath(absolute)) !== "") throw new EntryChanged();
  const file = await open(absolute, READ_FLAGS);
  try {
    // Windows ne fournit pas O_NOFOLLOW à Node. On compare l'identité du descripteur et celle
    // du chemin ainsi que ses ancêtres avant de lire des octets, puis après avoir fini.
    checkFile(stat, await file.stat(STAT_OPTIONS));
    await checkDirectories(directories);
    checkFile(stat, await lstat(absolute, STAT_OPTIONS));
    const result = await digest(file, Number(stat.size), signature, capture);
    checkFile(stat, await file.stat(STAT_OPTIONS));
    await checkDirectories(directories);
    checkFile(stat, await lstat(absolute, STAT_OPTIONS));
    return result;
  } finally {
    await file.close();
  }
}

function markIncomplete(result, error) {
  result.complete = false;
  if (error instanceof EntryChanged || ["ENOENT", "ENOTDIR", "ELOOP"].includes(error?.code)) {
    result.ignored.changed += 1;
  } else {
    result.ignored.unreadable += 1;
  }
}

async function visit(result, directories, absolute, path, name) {
  if (!validComponent(name)) {
    result.ignored.path += 1;
    return;
  }
  await checkDirectories(directories);
  const stat = await lstat(absolute, STAT_OPTIONS);
  const excluded = stat.isDirectory()
    ? result.exclusions.directories.has(path.toLowerCase())
    : stat.isFile() && result.exclusions.extensions.has(extname(path).toLowerCase());
  if (stat.isSymbolicLink() || (stat.isFile() && stat.nlink !== 1n)) {
    result.ignored.link += 1;
  } else if (TECHNICAL.has(name.toLowerCase())) {
    result.ignored.technical += 1;
  } else if (excluded) {
    result.ignored.excluded += 1;
  } else if (stat.isDirectory()) {
    await walk(result, [...directories, { absolute, stat }], path);
  } else if (stat.isFile()) {
    await visitFile(result, directories, absolute, path, stat);
  } else {
    result.ignored.special += 1;
  }
}

async function visitFile(result, directories, absolute, path, stat) {
  const extension = extname(path).toLowerCase();
  const signature = DOCUMENT_SIGNATURES.get(extension);
  if (!TEXT.has(extension) && !signature) {
    result.ignored.extension += 1;
  } else if (stat.size > MAX_SIZE) {
    result.ignored.tooLarge += 1;
  } else {
    const info = await fingerprint(directories, absolute, stat, signature);
    if (info) result.inventory.set(path, info);
    else result.ignored.binary += 1;
  }
}

async function walk(result, directories, prefix) {
  const { absolute } = directories.at(-1);
  const before = await checkDirectories(directories);
  const names = await readdir(absolute);
  checkTimestamps(before, await checkDirectories(directories));
  for (const name of names) {
    const path = prefix ? `${prefix}/${name}` : name;
    try {
      await visit(result, directories, join(absolute, name), path, name);
    } catch (error) {
      markIncomplete(result, error);
    }
  }
  checkTimestamps(before, await checkDirectories(directories));
}

// Les sous-arbres techniques ignorés comptent pour une entrée. Un parcours incomplet ne rend
// jamais les fichiers manquants supprimables. Les signatures seules filtrent PDF et DOCX ici.
export async function scanSyncFiles(root, { excluded_directories = [], excluded_extensions = [] } = {}) {
  const directories = await rootDirectories(root);
  const result = {
    inventory: new Map(),
    exclusions: {
      directories: new Set(excluded_directories.map((path) => path.toLowerCase())),
      extensions: new Set(excluded_extensions.map((extension) => extension.toLowerCase())),
    },
    ignored: { technical: 0, link: 0, extension: 0, binary: 0, tooLarge: 0,
      path: 0, special: 0, unreadable: 0, changed: 0, excluded: 0 },
    complete: true,
  };
  try {
    await walk(result, directories, "");
  } catch (error) {
    markIncomplete(result, error);
  }
  const ordered = [...result.inventory.keys()].sort().map((path) => [path, result.inventory.get(path)]);
  return { inventory: new Map(ordered), ignored: result.ignored, complete: result.complete };
}

export function diffSyncFiles(previous, scan) {
  if (!scan.complete) throw new ScanError("sync_scan_incomplete");
  const result = { added: [], changed: [], removed: [], unchanged: 0 };
  for (const path of [...scan.inventory.keys()].sort()) {
    const current = scan.inventory.get(path);
    const before = previous.get(path);
    if (!before) result.added.push({ path, ...current });
    else if (before.size !== current.size || before.sha256 !== current.sha256) {
      result.changed.push({ path, ...current });
    }
    else result.unchanged += 1;
  }
  result.removed = [...previous.keys()].filter((path) => !scan.inventory.has(path)).sort();
  return result;
}

// Relit la version inventoriée avant l'envoi. Un fichier qui a bougé attend le prochain scan.
export async function readSyncFile(root, path, expected) {
  if (typeof path !== "string" || !Number.isSafeInteger(expected?.size) ||
      expected.size < 0 || expected.size > MAX_SYNC_FILE_BYTES ||
      typeof expected.sha256 !== "string" || !/^[a-f0-9]{64}$/u.test(expected.sha256)) {
    return null;
  }
  const parts = path.split("/");
  if (parts.some((part) => !validComponent(part) || TECHNICAL.has(part.toLowerCase()))) return null;
  const fileName = parts.pop();
  const extension = extname(fileName).toLowerCase();
  const signature = DOCUMENT_SIGNATURES.get(extension);
  if (!TEXT.has(extension) && !signature) return null;
  const directories = await rootDirectories(root);
  try {
    for (const part of parts) {
      await checkDirectories(directories);
      const absolute = join(directories.at(-1).absolute, part);
      const stat = await lstat(absolute, STAT_OPTIONS);
      if (!stat.isDirectory()) return null;
      directories.push({ absolute, stat });
    }
    await checkDirectories(directories);
    const absolute = join(directories.at(-1).absolute, fileName);
    const stat = await lstat(absolute, STAT_OPTIONS);
    if (!stat.isFile() || stat.nlink !== 1n || stat.size !== BigInt(expected.size)) return null;
    const info = await fingerprint(directories, absolute, stat, signature, true);
    return info?.sha256 === expected.sha256 ? info.bytes : null;
  } catch {
    return null;
  }
}
