// Similaridade por conjunto de tokens (Jaccard), sem dependências externas.
// Objetivo: aproximar perguntas escritas diferente ("último acompanhamento do João"
// vs "quando foi a última vez que o João teve acompanhamento") da mesma intenção,
// sem exigir match exato de palavras-chave.

const STOPWORDS = new Set([
  'o', 'a', 'os', 'as', 'de', 'da', 'do', 'das', 'dos', 'um', 'uma', 'uns', 'umas',
  'que', 'foi', 'foram', 'foi', 'em', 'no', 'na', 'nos', 'nas', 'para', 'por',
  'com', 'sem', 'e', 'ou', 'se', 'ao', 'aos', 'à', 'às', 'é', 'ser', 'está',
  'quando', 'qual', 'quais', 'quem', 'onde', 'como', 'determinada', 'determinado',
]);

export function normalize(text) {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // remove acentos
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function tokenize(text) {
  return normalize(text)
    .split(' ')
    .filter((token) => token.length > 0 && !STOPWORDS.has(token));
}

export function jaccardSimilarity(textA, textB) {
  const tokensA = new Set(tokenize(textA));
  const tokensB = new Set(tokenize(textB));
  if (tokensA.size === 0 || tokensB.size === 0) return 0;

  let intersection = 0;
  for (const token of tokensA) {
    if (tokensB.has(token)) intersection += 1;
  }
  const union = tokensA.size + tokensB.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

// Similaridade "melhor de N" — compara o texto do usuário contra várias
// variações de exemplo de uma mesma intenção e retorna o maior score.
export function bestSimilarityAgainstPatterns(userText, patterns) {
  let best = 0;
  for (const pattern of patterns) {
    const score = jaccardSimilarity(userText, pattern);
    if (score > best) best = score;
  }
  return best;
}
