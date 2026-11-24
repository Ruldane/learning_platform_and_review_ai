import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeEvents } from "../fixtures";
import { EventTimeline } from "./EventTimeline";

describe("EventTimeline", () => {
  it("lists the events from the oldest to the newest, whatever the order given", () => {
    render(<EventTimeline events={makeEvents()} />);
    const items = within(
      screen.getByRole("list", { name: "Application history" }),
    ).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Application created");
    expect(items[1]).toHaveTextContent("Status change");
    expect(items[2]).toHaveTextContent("Note");
  });

  it("dates each event with a machine-readable time element", () => {
    render(<EventTimeline events={makeEvents()} />);
    const times = document.querySelectorAll("time");
    expect(times).toHaveLength(3);
    expect(times[0]).toHaveAttribute("datetime", "2026-11-03T08:00:00Z");
    expect(times[0]?.textContent).toMatch(/^03\/11\/2026/);
  });

  it("writes a status change as from → to, with the statuses in words", () => {
    render(<EventTimeline events={makeEvents()} />);
    expect(screen.getByText("To apply → Applied")).toBeInTheDocument();
  });

  it("shows the text of a note", () => {
    render(<EventTimeline events={makeEvents()} />);
    expect(screen.getByText("Appel avec la RH")).toBeInTheDocument();
  });

  it("writes a status with no previous one as a plain status", () => {
    render(
      <EventTimeline
        events={[
          {
            id: "e",
            kind: "status",
            at: "2026-11-03T08:00:00Z",
            statusFrom: null,
            statusTo: "offer",
            text: null,
          },
        ]}
      />,
    );
    expect(screen.getByText("Status: Offer")).toBeInTheDocument();
  });

  it("names every kind of event of the thread", () => {
    const kinds = ["reminder", "kit", "interview", "committee", "version"] as const;
    render(
      <EventTimeline
        events={kinds.map((kind, index) => ({
          id: `e${index}`,
          kind,
          at: `2026-11-0${index + 1}T08:00:00Z`,
          statusFrom: null,
          statusTo: null,
          text: null,
        }))}
      />,
    );
    for (const label of [
      "Follow-up",
      "Application kit",
      "Practice interview",
      "Hiring committee",
      "Résumé version",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("says so when there is no event", () => {
    render(<EventTimeline events={[]} />);
    expect(screen.getByText("Nothing in the history yet.")).toBeInTheDocument();
  });
});
