import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UserMessageBubble } from "./UserMessageBubble";

describe("UserMessageBubble", () => {
  it("shows the message with its author label", () => {
    render(<UserMessageBubble text="Keep beginners in mind" />);
    expect(screen.getByText("Keep beginners in mind")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
  });

  it("shows a command label", () => {
    render(<UserMessageBubble text="" command="shorter" />);
    expect(screen.getByText("Command: Shorter")).toBeInTheDocument();
  });

  it("shows the text of a command that has one", () => {
    render(<UserMessageBubble text="Skip the theory" command="more_concrete" />);
    expect(screen.getByText("Command: More concrete")).toBeInTheDocument();
    expect(screen.getByText("Skip the theory")).toBeInTheDocument();
  });
});
