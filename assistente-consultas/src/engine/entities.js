// Extração de entidades por regras + listas conhecidas do "banco" (mock).
// Começa simples (regex + lookup), conforme o prompt: evoluir depois para
// correspondência mais tolerante sem trocar a interface pro resto do motor.

const MONTHS = {
  janeiro: 1, fevereiro: 2, marco: 3, março: 3, abril: 4, maio: 5, junho: 6,
  julho: 7, agosto: 8, setembro: 9, outubro: 10, novembro: 11, dezembro: 12,
};

const RELATIVE_PERIODS = [
  { pattern: /\beste mes\b|\bneste mes\b|\bno mes\b/i, resolve: (today) => monthRange(today.getFullYear(), today.getMonth() + 1) },
  { pattern: /\bhoje\b/i, resolve: (today) => dayRange(today) },
  { pattern: /\b(ultim[ao]s?)\s+(\d+)\s+dias?\b/i, resolve: (today, match) => lastNDaysRange(today, Number(match[2])) },
  { pattern: /\b(ultim[ao]s?)\s+(\d+)\s+semanas?\b/i, resolve: (today, match) => lastNDaysRange(today, Number(match[2]) * 7) },
];

function pad(n) {
  return String(n).padStart(2, '0');
}

function toISODate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function dayRange(date) {
  return { start: toISODate(date), end: toISODate(date) };
}

function monthRange(year, month) {
  const start = new Date(year, month - 1, 1);
  const end = new Date(year, month, 0);
  return { start: toISODate(start), end: toISODate(end) };
}

function lastNDaysRange(today, n) {
  const start = new Date(today);
  start.setDate(start.getDate() - n);
  return { start: toISODate(start), end: toISODate(today) };
}

// Datas absolutas dd/mm ou dd/mm/aaaa
function extractExplicitDate(text, today) {
  const match = text.match(/\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/);
  if (!match) return null;
  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = match[3] ? Number(match[3].length === 2 ? `20${match[3]}` : match[3]) : today.getFullYear();
  const date = new Date(year, month - 1, day);
  if (Number.isNaN(date.getTime())) return null;
  return toISODate(date);
}

function extractMonthName(text) {
  const normalized = text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
  for (const [name, month] of Object.entries(MONTHS)) {
    const normalizedName = name.normalize('NFD').replace(/[̀-ͯ]/g, '');
    if (normalized.includes(normalizedName)) return month;
  }
  return null;
}

function stripAccents(text) {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

export function extractPeriod(text, today = new Date()) {
  const normalized = stripAccents(text);
  for (const { pattern, resolve } of RELATIVE_PERIODS) {
    const match = normalized.match(pattern);
    if (match) return resolve(today, match);
  }
  const monthName = extractMonthName(text);
  if (monthName) return monthRange(today.getFullYear(), monthName);
  return null;
}

export function extractDate(text, today = new Date()) {
  const explicit = extractExplicitDate(text, today);
  if (explicit) return explicit;
  if (/\bhoje\b/i.test(stripAccents(text))) return toISODate(today);
  return null;
}

// Nome de pessoa: aproximação por lookup contra os cadastros conhecidos —
// evita "adivinhar" nomes que não existem na base.
export function extractPerson(text, knownPeople) {
  const normalizedText = text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');

  let bestMatch = null;
  for (const person of knownPeople) {
    const firstName = person.nome.split(' ')[0].toLowerCase();
    const normalizedName = firstName.normalize('NFD').replace(/[̀-ͯ]/g, '');
    if (normalizedText.includes(normalizedName)) {
      if (!bestMatch || normalizedName.length > bestMatch.matchedLength) {
        bestMatch = { person, matchedLength: normalizedName.length };
      }
    }
  }
  return bestMatch ? bestMatch.person : null;
}
