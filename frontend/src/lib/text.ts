/** Lowercase and without accents, to compare with what the user types: «union sovietica» finds «Unión Soviética». */
export function fold(text: string): string {
  return text.normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('es').trim()
}
