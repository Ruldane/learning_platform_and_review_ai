import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ExportCard } from "./ExportCard";

const EXPORT_URL = "http://localhost:8000/api/v1/account/export";

describe("ExportCard", () => {
  it("export link targets the API", () => {
    render(<ExportCard href={EXPORT_URL} />);
    const link = screen.getByRole("link", { name: "Exporter toutes mes données" });
    expect(link).toHaveAttribute("href", EXPORT_URL);
    expect(screen.getByRole("heading", { name: "Exporter" })).toBeVisible();
  });

  it("says what the archive holds and that keys are never in it", () => {
    render(<ExportCard href="/x" />);
    const text = screen.getByRole("region", { name: "Exporter" });
    expect(text).toHaveTextContent("archive zip");
    expect(text).toHaveTextContent("Elle ne contient jamais tes clés d'API");
  });

  it("opens the download in a new tab, so an error page never replaces the application", () => {
    render(<ExportCard href={EXPORT_URL} />);
    const link = screen.getByRole("link", { name: "Exporter toutes mes données" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link).toHaveAttribute("download");
    expect(link).toHaveAccessibleDescription(
      "Le téléchargement s'ouvre dans un nouvel onglet ; " +
        "si la session a expiré, reconnecte-toi puis réessaie.",
    );
  });
});
