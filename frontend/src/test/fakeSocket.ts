import type { SessionEvent } from "@/shared/realtime/types";
import type { SocketFactory, SocketLike } from "@/shared/realtime/socket";

/** Fake WebSocket driven by the test: no network, each callback triggered by hand. */
export class FakeSocket implements SocketLike {
  readonly url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  /** `close()` called by the client. */
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

  /** Raw frame (for invalid frames). */
  pushRaw(data: string): this {
    this.onmessage?.({ data });
    return this;
  }

  /** Close from the server or network (1000 end, 1006 cut or refusal before accept). */
  drop(code: number): this {
    this.onclose?.({ code });
    return this;
  }
}

export interface FakeSocketServer {
  factory: SocketFactory;
  sockets: FakeSocket[];
  last(): FakeSocket;
  /** Sockets neither closed by the client nor unplugged (no more close callback). */
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
