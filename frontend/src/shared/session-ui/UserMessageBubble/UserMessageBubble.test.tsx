import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UserMessageBubble } from "./UserMessageBubble";

describe("UserMessageBubble", () => {
  it("shows the message with its author label", () => {
    render(<UserMessageBubble text="Pense aux débutants" />);
    expect(screen.getByText("Pense aux débutants")).toBeInTheDocument();
    expect(screen.getByText("Toi")).toBeInTheDocument();
  });

  it("shows a command label", () => {
    render(<UserMessageBubble text="" command="shorter" />);
    expect(screen.getByText("Commande : Plus court")).toBeInTheDocument();
  });

  it("shows the text of a command that has one", () => {
    render(<UserMessageBubble text="Sans théorie" command="more_concrete" />);
    expect(screen.getByText("Commande : Plus concret")).toBeInTheDocument();
    expect(screen.getByText("Sans théorie")).toBeInTheDocument();
  });
});
