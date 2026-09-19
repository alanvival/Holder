// Formatos de resposta que a camada de dados devolve — sempre estruturados,
// nunca texto livre gerado. A UI decide como renderizar cada `kind`.

export function textResponse(text) {
  return { kind: 'text', text };
}

export function dateResponse(text, isoDate) {
  return { kind: 'date', text, date: formatDatePt(isoDate) };
}

export function listResponse(text, items, contexto) {
  // items: [{ label }]
  return { kind: 'list', text, items, contexto };
}

export function locationResponse(text, local) {
  return { kind: 'location', text, local };
}

// Resposta de métrica agregada: valor em destaque (já formatado) + linha
// menor de contexto declarando o universo considerado (item 4 das "Regras
// de cálculo" do prompt de métricas — nunca um número solto).
export function metricResponse(text, valor, contexto) {
  return { kind: 'metric', text, valor, contexto };
}

export function notFoundResponse() {
  return { kind: 'not_found' };
}

export function formatDatePt(isoDate) {
  const [year, month, day] = isoDate.split('-');
  return `${day}/${month}/${year}`;
}

// mes_ref na base do desafio INOVAAPPS vem como "AAAA-MM" (sem dia).
export function formatMesPt(mesRef) {
  const [year, month] = mesRef.split('-');
  return `${month}/${year}`;
}

// --- Formatação numérica em padrão brasileiro, por tipo de métrica ---
// (regra do prompt de métricas: moeda com 2 casas, horas/percentual/dias
// com 1 casa, sempre vírgula decimal).

function comCasas(valor, casas) {
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function formatMoeda(valor) {
  return `R$ ${comCasas(valor, 2)}`;
}

export function formatHoras(valor) {
  return `${comCasas(valor, 1)} h`;
}

export function formatPercentual(valor) {
  return `${comCasas(valor, 1)}%`;
}

export function formatDias(valor) {
  return `${comCasas(valor, 1)} dia(s)`;
}

export function formatNumeroDecimal(valor, casas = 2) {
  return comCasas(valor, casas);
}

export function formatInteiro(valor) {
  return Math.round(valor).toLocaleString('pt-BR');
}
