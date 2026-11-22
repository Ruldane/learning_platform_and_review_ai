const GROUP_SIZE = 3;
const MIN_RESPONSE_MS = 300;
const MAX_RESPONSE_MS = 90_000;
const MAX_IDLE_MS = 30_000;
const MIN_SLOWDOWN_MS = 1_500;
const SLOWDOWN_RATIO = 1.4;
const MIN_EXTRA_ERRORS = 2;

export interface ResponseTiming {
  id: string;
  milliseconds: number;
}

export interface Observation {
  milliseconds: number;
  missed: boolean;
}

function eligible(milliseconds: number) {
  return (
    Number.isFinite(milliseconds) &&
    MIN_RESPONSE_MS <= milliseconds &&
    milliseconds <= MAX_RESPONSE_MS
  );
}

function median(group: Observation[]) {
  const ordered = group.map(({ milliseconds }) => milliseconds).sort((a, b) => a - b);
  return ordered[1]!;
}

/** Compare deux groupes disjoints de réponses réellement mesurées et évaluées. */
export function concentrationDrop(observations: readonly Observation[]): boolean {
  const observed = observations.filter(({ milliseconds }) => eligible(milliseconds));
  if (observed.length < 2 * GROUP_SIZE) return false;
  const early = observed.slice(0, GROUP_SIZE);
  const latest = observed.slice(-GROUP_SIZE);
  const errors = (group: Observation[]) => group.filter(({ missed }) => missed).length;
  const before = median(early);
  const after = median(latest);
  return (
    errors(latest) - errors(early) >= MIN_EXTRA_ERRORS &&
    after >= before * SLOWDOWN_RATIO &&
    after - before >= MIN_SLOWDOWN_MS
  );
}

/** Un intervalle trop long ou un onglet masqué invalide la mesure en cours. */
export class ResponseClock {
  private readonly now: () => number;
  private last: number | null = null;
  private elapsed = 0;
  private interrupted = false;

  constructor(now: () => number) {
    this.now = now;
  }

  restart() {
    this.last = this.now();
    this.elapsed = 0;
    this.interrupted = false;
  }

  interrupt() {
    this.interrupted = true;
  }

  activity() {
    const current = this.now();
    if (this.last === null) return;
    const delta = current - this.last;
    this.last = current;
    if (delta < 0 || delta > MAX_IDLE_MS) this.interrupt();
    this.elapsed += delta;
  }

  take(): number | null {
    this.activity();
    const duration = Math.round(this.elapsed);
    const value = this.interrupted || !eligible(duration) ? null : duration;
    this.restart();
    return value;
  }
}
