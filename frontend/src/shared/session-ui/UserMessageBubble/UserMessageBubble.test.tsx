import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UserMessageBubble } from "./UserMessageBubble";

describe("UserMessageBubble", () => {
  it("shows the message with its author label", () => {
    render(<UserMessageBubble text="Pense aux débutants" />);
    expect(screen.getByText("Pense aux débutants")).toBeInTheDocument();
    expect(screen.getByText("Toi")).toBeInTheDocument();
  });
});
