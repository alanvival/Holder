// Formatos de resposta que a camada de dados devolve — sempre estruturados,
// nunca texto livre gerado. A UI decide como renderizar cada `kind`.

export function textResponse(text) {
  return { kind: 'text', text };
}

export function dateResponse(text, isoDate) {
  return { kind: 'date', text, date: formatDatePt(isoDate) };
}

export function listResponse(text, items) {
  // items: [{ label }]
  return { kind: 'list', text, items };
}

export function locationResponse(text, local) {
  return { kind: 'location', text, local };
}

export function notFoundResponse() {
  return { kind: 'not_found' };
}

export function formatDatePt(isoDate) {
  const [year, month, day] = isoDate.split('-');
  return `${day}/${month}/${year}`;
}
