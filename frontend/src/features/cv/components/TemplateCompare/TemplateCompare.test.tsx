import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ZoneView } from "../viewTypes";
import { TemplateCompare } from "./TemplateCompare";
import { zoneSentences } from "./zoneSentences";

const ZONES: ZoneView[] = [
  { zone: "left", original: 0.4, render: 0.22 },
  { zone: "top", original: 0.3, render: 0.31 },
  { zone: "bottom", original: 0.1, render: 0.2 },
];

function setup(props: Partial<Parameters<typeof TemplateCompare>[0]> = {}) {
  render(
    <TemplateCompare
      originalPages={["/o1.png", "/o2.png"]}
      renderPages={["/r1.png", "/r2.png"]}
      score={87}
      zones={ZONES}
      passes={2}
      {...props}
    />,
  );
}

describe("TemplateCompare", () => {
  it("shows the two columns, page by page, with their alternative texts", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Your CV" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recreated template" })).toBeInTheDocument();
    const page2 = screen.getByRole("region", { name: "Page 2" });
    expect(within(page2).getByRole("img", { name: "Page 2 of your original CV" })).toHaveAttribute(
      "src",
      "/o2.png",
    );
    expect(
      within(page2).getByRole("img", { name: "Page 2 of the recreated template" }),
    ).toHaveAttribute("src", "/r2.png");
    expect(screen.getAllByRole("img")).toHaveLength(4);
  });

  it("shows the score, the passes and the zones as sentences", () => {
    setup();
    expect(screen.getByText("Similarity: 87%")).toBeInTheDocument();
    expect(screen.getByText("After 2 adjustments.")).toBeInTheDocument();
    const items = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(items).toEqual([
      "The recreated template has 18% less ink on the left than your CV.",
      "The recreated template has 10% more ink at the bottom than your CV.",
    ]);
  });

  it("says when the score is not computed, and when no zone differs", () => {
    setup({ score: null, zones: [] });
    expect(screen.getByText("Similarity: not calculated yet")).toBeInTheDocument();
    expect(screen.queryByText("Where the recreated template differs")).not.toBeInTheDocument();
  });

  it("says when no zone stands out", () => {
    setup({ zones: [{ zone: "top", original: 0.3, render: 0.31 }], passes: 0 });
    expect(screen.getByText("No notable layout differences.")).toBeInTheDocument();
    expect(screen.getByText("No adjustments.")).toBeInTheDocument();
  });

  it("says when a page is missing on one side", () => {
    setup({ renderPages: ["/r1.png"] });
    expect(screen.getByText("No page 2 on this side.")).toBeInTheDocument();
  });

  it("switches to the overlay with a keyboard-operable slider", async () => {
    setup();
    const overlay = screen.getByRole("button", { name: "Overlay" });
    expect(screen.getByRole("button", { name: "Side by side" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(overlay);
    expect(overlay).toHaveAttribute("aria-pressed", "true");
    const slider = screen.getByRole("slider", { name: "Comparison slider" });
    expect(slider).toHaveAttribute("aria-valuetext", "Your CV up to 50% of the width");
    // Once focused, the native slider can be adjusted with the arrow keys.
    await userEvent.tab();
    expect(slider).toHaveFocus();
    fireEvent.change(slider, { target: { value: "20" } });
    expect(slider).toHaveAttribute("aria-valuetext", "Your CV up to 20% of the width");
    expect(screen.getByRole("img", { name: "Page 1 of your original CV" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Page 1 of the recreated template" })).toBeInTheDocument();
  });

  it("says when there is nothing to compare", () => {
    setup({ originalPages: [], renderPages: [] });
    expect(screen.getByText("No pages to compare yet.")).toBeInTheDocument();
  });
});

describe("zoneSentences", () => {
  it("keeps the four biggest gaps over five points", () => {
    const zones: ZoneView[] = [
      { zone: "top", original: 0.1, render: 0.2 },
      { zone: "middle", original: 0.1, render: 0.3 },
      { zone: "bottom", original: 0.5, render: 0.2 },
      { zone: "left", original: 0.1, render: 0.17 },
      { zone: "right", original: 0.1, render: 0.15 },
    ];
    expect(zoneSentences(zones)).toHaveLength(4);
    expect(zoneSentences(zones)[0]).toBe(
      "The recreated template has 30% less ink at the bottom than your CV.",
    );
  });
});
