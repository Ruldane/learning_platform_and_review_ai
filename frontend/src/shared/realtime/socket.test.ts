import { afterEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { browserSocket, parseEventFrame, sessionStreamUrl } from "./socket";
import { tok } from "./testEvents";

class StubWebSocket {
  static last: StubWebSocket | null = null;
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: unknown }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  close = vi.fn();
  constructor(url: string) {
    this.url = url;
    StubWebSocket.last = this;
  }
}

describe("socket", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("builds the ws url from the API base url", () => {
    const expected = apiBaseUrl.replace(/^http/, "ws");
    expect(sessionStreamUrl("s 1", 7)).toBe(`${expected}/api/v1/sessions/s%201/stream?after_seq=7`);
    expect(sessionStreamUrl("s1", 0).startsWith("ws")).toBe(true);
  });

  it("parses session events and rejects anything else", () => {
    const event = tok(3, "m1", "Bon");
    expect(parseEventFrame(JSON.stringify(event))).toEqual(event);
    expect(parseEventFrame("{")).toBeNull();
    expect(parseEventFrame("[]")).toBeNull();
    expect(parseEventFrame('{"seq":"1","type":"agent.token"}')).toBeNull();
    expect(parseEventFrame('{"seq":1.5,"type":"agent.token"}')).toBeNull();
  });

  it("adapts the browser WebSocket", () => {
    vi.stubGlobal("WebSocket", StubWebSocket);
    const socket = browserSocket("ws://x/stream");
    const ws = StubWebSocket.last!;
    const seen: unknown[] = [];
    socket.onopen = () => seen.push("open");
    socket.onmessage = (e) => seen.push(e.data);
    socket.onclose = (e) => seen.push(e.code);
    ws.onopen?.();
    ws.onmessage?.({ data: "texte" });
    ws.onmessage?.({ data: new ArrayBuffer(2) });
    ws.onclose?.({ code: 1006 });
    socket.close();
    expect(ws.url).toBe("ws://x/stream");
    expect(seen).toEqual(["open", "texte", 1006]);
    expect(ws.close).toHaveBeenCalledOnce();
  });
});
