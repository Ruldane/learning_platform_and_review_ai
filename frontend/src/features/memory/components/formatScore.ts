/** Score de similarité à deux décimales, avec la virgule française (`0.834` devient « 0,83 »). */
export function formatScore(score: number): string {
  return score.toFixed(2).replace(".", ",");
}
