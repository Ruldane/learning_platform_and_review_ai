import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { registerEventRenderer } from "@/shared/realtime/eventRenderers";
import { sourceFound } from "@/shared/realtime/testEvents";
import type { FeedItem } from "@/shared/realtime/types";
import { DebateFeed } from "./DebateFeed";

const turn: FeedItem = {
  kind: "turn",
  messageId: "m1",
  agent: "demo_critic",
  intent: "je relis",
  text: "Premier avis",
  streaming: false,
  tools: [],
  citations: [],
};
const user: FeedItem = { kind: "user", seq: 2, text: "Pense aux débutants", command: null };
const interrupt: FeedItem = {
  kind: "interrupt",
  seq: 3,
  answered: false,
  interrupt: { interrupt_id: "i1", kind: "choice", question: "Quelle suite ?", options: [] },
};

let unregister: (() => void) | undefined;
afterEach(() => unregister?.());

describe("DebateFeed", () => {
  it("renders the citations of a turn and the command of a user message", () => {
    const cited: FeedItem = {
      ...turn,
      messageId: "m2",
      citations: [{ index: 1, title: "Doc", url: "https://a.org", memory_item_id: null }],
    } as FeedItem;
    const command: FeedItem = { kind: "user", seq: 4, text: "", command: "to_proposals" };
    render(<DebateFeed items={[cited, command]} renderInterrupt={() => null} />);
    expect(screen.getByRole("link", { name: "Source 1 : Doc" })).toBeInTheDocument();
    expect(screen.getByText("Commande : Passer aux propositions")).toBeInTheDocument();
  });

  it("renders turns, user messages and delegates interrupts to renderInterrupt", () => {
    render(
      <DebateFeed
        items={[turn, user, interrupt]}
        renderInterrupt={(item) => <p>carte {item.interrupt.interrupt_id}</p>}
      />,
    );
    expect(screen.getByText("Premier avis")).toBeInTheDocument();
    expect(screen.getByText("Pense aux débutants")).toBeInTheDocument();
    expect(screen.getByText("carte i1")).toBeInTheDocument();
  });

  it("renders a registered renderer for generic events", () => {
    unregister = registerEventRenderer("source.found", ({ event }) => <p>source {event.id}</p>);
    const event = sourceFound(7);
    render(<DebateFeed items={[{ kind: "event", event }]} renderInterrupt={() => null} />);
    expect(screen.getByText(`source ${event.id}`)).toBeInTheDocument();
  });

  it("skips generic events that have no renderer", () => {
    const items: FeedItem[] = [{ kind: "event", event: sourceFound(8) }];
    render(<DebateFeed items={items} renderInterrupt={() => null} />);
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });

  it("is a labelled list in order, with a message when empty", () => {
    const { rerender } = render(<DebateFeed items={[turn, user]} renderInterrupt={() => null} />);
    expect(screen.getByRole("list", { name: "Fil du débat" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    rerender(<DebateFeed items={[]} renderInterrupt={() => null} />);
    expect(screen.getByText("Le débat va commencer…")).toBeInTheDocument();
  });
});
