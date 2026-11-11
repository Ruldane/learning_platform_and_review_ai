import type { SessionEvent } from "@/shared/realtime/types";
import type { SocketFactory, SocketLike } from "@/shared/realtime/socket";

/** Faux WebSocket piloté par le test : aucun réseau, chaque rappel déclenché à la main. */
export class FakeSocket implements SocketLike {
  readonly url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  /** `close()` appelé par le client. */
  closedByClient = false;

  constructor(url: string) {
    this.url = url;
  }

  close(): void {
    this.closedByClient = true;
  }

  open(): this {
    this.onopen?.();
    return this;
  }

  push(...events: SessionEvent[]): this {
    for (const event of events) this.onmessage?.({ data: JSON.stringify(event) });
    return this;
  }

  /** Trame brute (pour les trames invalides). */
  pushRaw(data: string): this {
    this.onmessage?.({ data });
    return this;
  }

  /** Fermeture côté serveur ou réseau (1000 fin, 1006 coupure ou refus avant accept). */
  drop(code: number): this {
    this.onclose?.({ code });
    return this;
  }
}

export interface FakeSocketServer {
  factory: SocketFactory;
  sockets: FakeSocket[];
  last(): FakeSocket;
  /** Sockets ni fermés par le client ni débranchés (plus de rappel de fermeture). */
  openSockets(): FakeSocket[];
}

export function createFakeSocketServer(): FakeSocketServer {
  const sockets: FakeSocket[] = [];
  return {
    sockets,
    factory: (url) => {
      const socket = new FakeSocket(url);
      sockets.push(socket);
      return socket;
    },
    last: () => {
      const socket = sockets.at(-1);
      if (!socket) throw new Error("Aucun socket ouvert");
      return socket;
    },
    openSockets: () => sockets.filter((s) => !s.closedByClient && s.onclose !== null),
  };
}
