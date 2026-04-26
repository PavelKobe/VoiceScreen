// Транслитерация ГОСТ-7.79 (упрощённая) для генерации slug из русских названий.

const MAP: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "yo",
  ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l", м: "m",
  н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u",
  ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh", щ: "sch",
  ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
};

export function transliterate(input: string): string {
  let out = "";
  for (const ch of input.toLowerCase()) {
    out += MAP[ch] ?? ch;
  }
  return out;
}

/** Превратить произвольную строку в безопасный slug a-z0-9 с дефисами. */
export function slugify(input: string): string {
  return transliterate(input)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-")
    .slice(0, 100);
}
