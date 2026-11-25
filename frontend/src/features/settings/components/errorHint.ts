import { t } from "@/shared/i18n/t";

/**
 * A field's help: in error, it starts with « Erreur : ». The invalid state therefore never
 * relies on colour alone (the field's frame changes too: `aria-invalid` in `fieldClass`).
 */
export const errorHint = (bad: boolean, text: string): string =>
  bad ? `${t("settings.fields.errorPrefix")}${text}` : text;
