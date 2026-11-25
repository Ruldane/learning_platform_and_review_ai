import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ResearchBenchInput } from "../viewTypes";
import { BenchFields } from "./BenchFields";
import { parseBench } from "./parseBench";

interface ResearchBenchFormProps {
  onSubmit: (input: ResearchBenchInput) => void;
  launchMenu?: ReactNode;
  /** A test is running: the form is locked. */
  busy: boolean;
}

/** Test form: one query (2 to 300 characters) and up to 5 extra http(s) addresses. */
export function ResearchBenchForm({ onSubmit, busy, launchMenu }: ResearchBenchFormProps) {
  const [query, setQuery] = useState("");
  const [urls, setUrls] = useState("");
  const [errors, setErrors] = useState<{ query?: string; urls?: string }>({});

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const parsed = parseBench(query, urls);
    if (parsed.errors.query || parsed.errors.urls) return setErrors(parsed.errors);
    onSubmit(parsed.input);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <BenchFields
        query={query}
        urls={urls}
        errors={errors}
        disabled={busy}
        onQueryChange={(next) => {
          setQuery(next);
          setErrors({});
        }}
        onUrlsChange={(next) => {
          setUrls(next);
          setErrors({});
        }}
      />
      {launchMenu}
      <Button type="submit" disabled={busy} className="self-start">
        {busy ? t("research.bench.busy") : t("research.bench.submit")}
      </Button>
    </form>
  );
}
