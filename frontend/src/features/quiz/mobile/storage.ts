import { onLocalReset } from "@/shared/lib/localReset";
import type { Answer, MobileCard, MobileSnapshot, QueuedReview } from "./data";

const PREFIX = "tremplin:mobile:";
const GENERATION = "tremplin:mobile-generation";
const CHANGED = PREFIX + "changed";
let localGeneration: string | null = null;

export function mobileGeneration(): string {
  if (localGeneration !== null) return localGeneration;
  try {
    return localStorage.getItem(GENERATION) ?? "initial";
  } catch {
    return "initial";
  }
}

function generationPrefix(generation: string) {
  return `${PREFIX}${generation}:`;
}

function changed() {
  window.dispatchEvent(new Event(CHANGED));
}

export function subscribeMobile(listener: () => void) {
  window.addEventListener(CHANGED, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(CHANGED, listener);
    window.removeEventListener("storage", listener);
  };
}

export function mobileRevision() {
  try {
    const values = Object.keys(localStorage)
      .filter((key) => key.startsWith(PREFIX))
      .sort()
      .map((key) => localStorage.getItem(key));
    return [mobileGeneration(), ...values].join("\0");
  } catch {
    return "";
  }
}

function read<T>(key: string): T | null {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "null") as T | null;
  } catch {
    return null;
  }
}

export function cachedMobile(): MobileSnapshot | null {
  return read<MobileSnapshot>(generationPrefix(mobileGeneration()) + "snapshot");
}

function persistGeneration(generation: string) {
  localStorage.setItem(GENERATION, generation);
  localGeneration = null;
}

function writeCurrent(key: string, value: unknown, generation: string): boolean {
  if (mobileGeneration() !== generation) return false;
  if (localGeneration === generation) persistGeneration(generation);
  localStorage.setItem(key, JSON.stringify(value));
  if (mobileGeneration() !== generation) {
    localStorage.removeItem(key);
    return false;
  }
  changed();
  return true;
}

export function saveMobile(snapshot: MobileSnapshot, generation = mobileGeneration()) {
  return writeCurrent(generationPrefix(generation) + "snapshot", snapshot, generation);
}

function purgeMobile(generation: string) {
  const keep = generationPrefix(generation);
  for (const key of Object.keys(localStorage)) {
    if (key.startsWith(PREFIX) && !key.startsWith(keep)) localStorage.removeItem(key);
  }
}

export function clearMobile() {
  const next = crypto.getRandomValues(new Uint32Array(4)).join("-");
  localGeneration = next;
  try {
    // Libère d’abord l’espace nécessaire au marqueur, même si le quota est déjà atteint.
    purgeMobile(next);
    try {
      persistGeneration(next);
    } catch {
      purgeMobile(next);
      persistGeneration(next);
    }
    // Retire aussi une copie réécrite par un autre onglet avant la rotation du marqueur.
    purgeMobile(next);
  } catch {
    // Si le marqueur reste impossible à écrire, la génération locale reste invalidée.
  } finally {
    changed();
  }
}

onLocalReset(clearMobile);

function queuePrefix(generation: string, owner: string) {
  return `${generationPrefix(generation)}review:${owner}:`;
}

function reviewKey(review: Pick<QueuedReview, "owner" | "card" | "due">, generation: string) {
  return queuePrefix(generation, review.owner) + [review.card, review.due].join(":");
}

export function queueReview(
  owner: string,
  card: MobileCard,
  result: Answer,
  generation = mobileGeneration(),
) {
  const identity = { owner, card: card.id, due: card.due };
  const key = reviewKey(identity, generation);
  const review = read<QueuedReview>(key) ?? { ...identity, id: crypto.randomUUID(), result };
  return writeCurrent(key, review, generation) ? review : null;
}

export function pendingReviews(owner: string) {
  const prefix = queuePrefix(mobileGeneration(), owner);
  return Object.keys(localStorage)
    .filter((key) => key.startsWith(prefix))
    .flatMap((key) => {
      const review = read<QueuedReview>(key);
      return review?.owner === owner ? [review] : [];
    });
}

export function applyReview(review: QueuedReview, generation: string) {
  if (mobileGeneration() !== generation) return;
  const key = reviewKey(review, generation);
  if (read<QueuedReview>(key)?.id !== review.id) return;
  localStorage.removeItem(key);
  const snapshot = cachedMobile();
  if (snapshot?.owner === review.owner) {
    saveMobile(
      {
        ...snapshot,
        cards: snapshot.cards.filter((card) => card.id !== review.card || card.due !== review.due),
      },
      generation,
    );
  } else {
    changed();
  }
}
