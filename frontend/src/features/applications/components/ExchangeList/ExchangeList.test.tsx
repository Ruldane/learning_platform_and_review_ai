import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeExchange } from "../fixtures";
import { ExchangeList } from "./ExchangeList";

describe("ExchangeList", () => {
  it("says when a question has no answer", () => {
    render(
      <ExchangeList exchanges={[makeExchange(0, { answer: "" })]} missed={[]} expected={[]} />,
    );
    expect(screen.getByText("(no answer)")).toBeVisible();
  });

  it("shows no note for an unrated answer, whatever its number", () => {
    render(
      <ExchangeList
        exchanges={[makeExchange(0, { unrated: true, note: 3 })]}
        missed={[]}
        expected={[]}
      />,
    );
    expect(screen.getByText("Not scored")).toBeVisible();
    expect(screen.queryByText("Score: 3 out of 5")).toBeNull();
  });

  it("shows the answers without any note when there is no debrief (notes undefined)", () => {
    render(<ExchangeList exchanges={[makeExchange(0)]} showNotes={false} />);
    expect(screen.getByText("Ma réponse 1.")).toBeVisible();
    expect(screen.queryByText(/Score:/)).toBeNull();
  });
});
