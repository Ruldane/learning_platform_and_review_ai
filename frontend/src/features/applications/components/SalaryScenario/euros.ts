const formatEuros = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export const euros = (amount: number) => formatEuros.format(amount);
