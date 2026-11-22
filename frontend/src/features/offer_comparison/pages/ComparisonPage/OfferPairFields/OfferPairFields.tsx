import { t } from "@/shared/i18n/t";
import type { SourceOffer } from "../../../api";
import { OfferSelect } from "../OfferSelect";

interface Props {
  options: SourceOffer[];
  first: string;
  second: string;
  onFirst: (id: string) => void;
  onSecond: (id: string) => void;
}

export function OfferPairFields({ options, first, second, onFirst, onSecond }: Props) {
  return (
    <>
      <OfferSelect
        label={t("offerComparison.first")}
        value={first}
        options={options}
        excluded={second}
        onChange={onFirst}
      />
      <OfferSelect
        label={t("offerComparison.second")}
        value={second}
        options={options}
        excluded={first}
        onChange={onSecond}
      />
      {options.length < 2 && <p className="text-sm">{t("offerComparison.needTwo")}</p>}
    </>
  );
}
