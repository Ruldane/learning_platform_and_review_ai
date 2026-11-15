/** « 1 », « 1 et 3 », « 1, 2 et 3 » : des numéros de questions en français. */
export function joinNumbers(numbers: number[]): string {
  if (numbers.length <= 1) return numbers.join("");
  return `${numbers.slice(0, -1).join(", ")} et ${numbers[numbers.length - 1]}`;
}
