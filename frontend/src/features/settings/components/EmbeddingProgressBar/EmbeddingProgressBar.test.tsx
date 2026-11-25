import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmbeddingProgressBar } from "./EmbeddingProgressBar";

const progress = (over: object) => ({
  model: "bge-m3",
  present: false,
  percent: null,
  detail: "",
  ...over,
});

describe("EmbeddingProgressBar", () => {
  it("writes the percentage and fills the bar while the model downloads", () => {
    render(<EmbeddingProgressBar progress={progress({ percent: 42 })} isError={false} />);
    expect(screen.getByText("bge-m3: 42%")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Embedding model" });
    expect(bar).toHaveAttribute("value", "42");
    expect(bar).toHaveAttribute("max", "100");
  });

  it("says the model is ready, with a full bar", () => {
    render(
      <EmbeddingProgressBar progress={progress({ present: true, percent: 100 })} isError={false} />,
    );
    expect(screen.getByText("bge-m3: ready")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("value", "100");
  });

  it("shows an unknown size as a bar without a value, with the server's detail", () => {
    render(
      <EmbeddingProgressBar
        progress={progress({ detail: "Ollama ne répond pas." })}
        isError={false}
      />,
    );
    expect(screen.getByText("bge-m3: download pending")).toBeInTheDocument();
    expect(screen.getByText("Ollama ne répond pas.")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).not.toHaveAttribute("value");
  });

  it("says when the progress cannot be read", () => {
    render(<EmbeddingProgressBar isError />);
    expect(screen.getByRole("status")).toHaveTextContent("Could not read the model's progress");
  });

  it("announces that the model is ready, in a zone that was there before", () => {
    const { rerender } = render(
      <EmbeddingProgressBar progress={progress({ percent: 42 })} isError={false} />,
    );
    const zone = screen.getByRole("status");
    expect(zone).toBeEmptyDOMElement();
    rerender(
      <EmbeddingProgressBar progress={progress({ present: true, percent: 100 })} isError={false} />,
    );
    expect(screen.getByRole("status")).toBe(zone);
    expect(zone).toHaveTextContent("bge-m3: ready");
    expect(screen.getAllByText("bge-m3: ready")).toHaveLength(1);
  });

  it("keeps its zone, empty, before the first answer", () => {
    render(<EmbeddingProgressBar isError={false} />);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("is quiet before the first answer", () => {
    render(<EmbeddingProgressBar isError={false} />);
    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});
