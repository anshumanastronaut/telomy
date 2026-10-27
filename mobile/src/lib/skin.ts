// Fitzpatrick skin phototype (I–VI). Not cosmetic: melanin biases optical SpO₂ (occult hypoxaemia risk) and PPG
// signal quality, and it sets UV burn risk, safe-sun windows and vitamin-D synthesis — so it personalises the ring/
// patch oxygen reads and the outdoor/UV score. Stored on the profile as `skin_type` (1–6).
export type SkinType = 1 | 2 | 3 | 4 | 5 | 6;

export const FITZPATRICK: { type: SkinType; roman: string; swatch: string; desc: string }[] = [
  { type: 1, roman: 'I', swatch: '#F4D6BE', desc: 'Always burns, never tans' },
  { type: 2, roman: 'II', swatch: '#E8B894', desc: 'Usually burns, tans minimally' },
  { type: 3, roman: 'III', swatch: '#D2A074', desc: 'Sometimes burns, tans evenly' },
  { type: 4, roman: 'IV', swatch: '#B67A4E', desc: 'Rarely burns, tans easily' },
  { type: 5, roman: 'V', swatch: '#8C5733', desc: 'Very rarely burns, deeply tans' },
  { type: 6, roman: 'VI', swatch: '#5E3A27', desc: 'Never burns, deeply pigmented' },
];

export const skinLabel = (t?: number | null): string | null => {
  const f = FITZPATRICK.find((x) => x.type === t);
  return f ? `Skin type ${f.roman}` : null;
};
export const skinSwatch = (t?: number | null): string | null => FITZPATRICK.find((x) => x.type === t)?.swatch ?? null;
