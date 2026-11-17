import { t } from "@/shared/i18n/t";

/**
 * L'aide d'un champ : en erreur, elle commence par « Erreur : ». L'état invalide ne tient donc
 * jamais à la couleur seule (le cadre du champ change aussi : `aria-invalid` dans `fieldClass`).
 */
export const errorHint = (bad: boolean, text: string): string =>
  bad ? `${t("settings.fields.errorPrefix")}${text}` : text;
