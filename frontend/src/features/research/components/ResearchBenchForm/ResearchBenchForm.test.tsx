import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ResearchBenchForm } from "./ResearchBenchForm";

const QUERY = "Requête";
const URLS = "Adresses supplémentaires";
const SUBMIT = "Lancer l'essai";

describe("ResearchBenchForm", () => {
  it("envoie la requête et les adresses nettoyées, sans doublon", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ResearchBenchForm onSubmit={onSubmit} busy={false} />);
    await user.type(screen.getByLabelText(QUERY), "  rag en français  ");
    await user.click(screen.getByLabelText(URLS));
    await user.paste("https://a.org/x\n\n  http://b.org  \nhttps://a.org/x");
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledWith({
      query: "rag en français",
      urls: ["https://a.org/x", "http://b.org/"],
    });
  });

  it("accepte une requête sans adresse", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ResearchBenchForm onSubmit={onSubmit} busy={false} />);
    await user.type(screen.getByLabelText(QUERY), "rag{Enter}");
    expect(onSubmit).toHaveBeenCalledWith({ query: "rag", urls: [] });
  });

  it.each(["", " a ", "x".repeat(301)])("refuse la requête %j", async (typed) => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ResearchBenchForm onSubmit={onSubmit} busy={false} />);
    if (typed) {
      await user.click(screen.getByLabelText(QUERY));
      await user.paste(typed);
    }
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "La requête doit faire de 2 à 300 caractères.",
    );
    expect(screen.getByLabelText(QUERY)).toHaveAttribute("aria-invalid", "true");
  });

  it("refuse une adresse qui n'est pas http(s)", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ResearchBenchForm onSubmit={onSubmit} busy={false} />);
    await user.type(screen.getByLabelText(QUERY), "rag");
    await user.type(screen.getByLabelText(URLS), "ftp://exemple.org/fichier");
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Cette adresse doit commencer par http:// ou https:// : ftp://exemple.org/fichier",
    );
  });

  it("refuse plus de cinq adresses", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ResearchBenchForm onSubmit={onSubmit} busy={false} />);
    await user.type(screen.getByLabelText(QUERY), "rag");
    await user.click(screen.getByLabelText(URLS));
    await user.paste(Array.from({ length: 6 }, (_, i) => `https://s${i}.org`).join("\n"));
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("5 adresses supplémentaires au plus.");
  });

  it("efface les erreurs dès qu'on corrige", async () => {
    const user = userEvent.setup();
    render(<ResearchBenchForm onSubmit={vi.fn()} busy={false} />);
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.type(screen.getByLabelText(QUERY), "r");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("désactive tout pendant l'essai", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ResearchBenchForm onSubmit={onSubmit} busy />);
    expect(screen.getByLabelText(QUERY)).toBeDisabled();
    expect(screen.getByLabelText(URLS)).toBeDisabled();
    const button = screen.getByRole("button", { name: "Essai en cours…" });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
