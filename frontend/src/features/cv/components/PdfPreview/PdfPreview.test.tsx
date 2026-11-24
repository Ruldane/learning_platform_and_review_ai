import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PdfPreview } from "./PdfPreview";

function setup(props: Partial<Parameters<typeof PdfPreview>[0]> = {}) {
  render(
    <PdfPreview
      pages={["/p1.png"]}
      pageCount={1}
      originalPageCount={1}
      filename="CV_Camille-Exemple_Societe-Fictive.pdf"
      downloadUrl="/api/cv/versions/v1/pdf"
      {...props}
    />,
  );
}

describe("PdfPreview", () => {
  it("shows the page images, with no embedded PDF reader", () => {
    const { container } = render(
      <PdfPreview
        pages={["/p1.png", "/p2.png"]}
        pageCount={2}
        originalPageCount={2}
        filename="CV.pdf"
        downloadUrl="/x"
      />,
    );
    expect(screen.getByRole("img", { name: "Page 1 of 2 of the CV" })).toHaveAttribute(
      "src",
      "/p1.png",
    );
    expect(screen.getByRole("img", { name: "Page 2 of 2 of the CV" })).toBeInTheDocument();
    expect(container.querySelector("iframe, embed, object")).toBeNull();
  });

  it("says the page count matches the original", () => {
    setup();
    expect(screen.getByText("1 page, like your original CV")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("warns when the CV has more pages than the original", () => {
    setup({ pages: ["/p1.png", "/p2.png"], pageCount: 2 });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "2 pages: your original CV has 1. Tighten the content or accept one more page.",
    );
  });

  it("says when the CV is shorter than the original", () => {
    setup({ pageCount: 1, originalPageCount: 2 });
    expect(screen.getByText("1 page; your original CV had 2.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("offers the download of the named file", () => {
    setup();
    const link = screen.getByRole("link", {
      name: "Download CV_Camille-Exemple_Societe-Fictive.pdf",
    });
    expect(link).toHaveAttribute("href", "/api/cv/versions/v1/pdf");
    expect(link).toHaveAttribute("download", "CV_Camille-Exemple_Societe-Fictive.pdf");
  });

  it("says when there is no page to show", () => {
    setup({ pages: [] });
    expect(screen.getByText("No pages to display.")).toBeInTheDocument();
  });
});
