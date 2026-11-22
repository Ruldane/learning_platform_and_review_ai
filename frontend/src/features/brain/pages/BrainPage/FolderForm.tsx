import { useState, type Ref } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { FolderIn } from "../../api";
import { FolderField } from "./FolderField";

interface FolderFormProps {
  busy: boolean;
  nameRef: Ref<HTMLInputElement>;
  onAdd: (data: FolderIn) => Promise<unknown>;
}

export function FolderForm({ busy, nameRef, onAdd }: FolderFormProps) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const add = async () => {
    if (busy || !name.trim() || !path.trim()) return;
    try {
      await onAdd({ name: name.trim(), path: path.trim(), paused: false });
      setName("");
      setPath("");
    } catch {
      // Les champs restent remplis pour le prochain essai.
    }
  };
  return (
    <form
      className="grid max-w-3xl gap-3 rounded-xl border border-border p-4 md:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        void add();
      }}
    >
      <FolderField
        label={t("brain.name")}
        maxLength={200}
        inputRef={nameRef}
        value={name}
        disabled={busy}
        onChange={setName}
      />
      <FolderField
        label={t("brain.path")}
        maxLength={2048}
        value={path}
        disabled={busy}
        onChange={setPath}
      />
      <Button
        type="submit"
        className="justify-self-start"
        disabled={busy || !name.trim() || !path.trim()}
      >
        {t("brain.add")}
      </Button>
    </form>
  );
}
