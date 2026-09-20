// Atalho determinístico pra família de perguntas sobre previsão de risco
// (faixa, tendência subindo/caindo/estável) — SEM passar pelo Groq.
//
// O dado (Score de Risco, tabela fScoreRisco) é uma leitura simples do
// histórico já persistido, não algo que precise de um modelo de linguagem
// pra ser buscado — mas antes desta rota, QUALQUER pergunta sobre risco
// (inclusive "quais clientes estão com risco subindo", que a própria aba
// "Quem Contatar" do dashboard já mostra na tela) só podia ser respondida
// pelo fallback de IA, sujeito a 30-105s de latência real do Groq (ver
// dados/gerado/logs/fallback_ia.log) e ao timeout de 45s do front — o
// usuário via "não encontrei" mesmo com o dado pronto e rápido de buscar.
// Reconhece o padrão da pergunta aqui e chama GET /api/risco/previsao
// direto (holder/interfaces/api/servidor.py), que só lê o histórico —
// tipicamente < 1s. Só cai no fallback de IA se o padrão não bater.

const PALAVRAS_RISCO = /\brisco\b|\bcancelamento\b|\bcancelar\b|previs[ãa]o|probabilidade/i;
const PALAVRAS_CLIENTES = /clientes?|empresas?/i;

const PADRAO_SUBINDO = /subindo|aumentando|piorando|crescendo|piora\b/i;
const PADRAO_CAINDO = /caindo|diminuindo|melhorando|reduzindo|melhora\b/i;
const PADRAO_ESTAVEL = /est[áa]vel|sem mudan[çc]a|parad[oa]/i;

const PADRAO_CRITICO = /cr[íi]tico/i;
const PADRAO_EM_RISCO = /\bem risco\b/i;
const PADRAO_ATENCAO = /aten[çc][ãa]o/i;
const PADRAO_SAUDAVEL = /saud[áa]vel/i;

// Um cliente_id específico na pergunta ("por que o C071...") pede
// explicabilidade individual, não a lista — fora do escopo deste atalho,
// deixa cair pro fallback de IA (detalhar_previsao_cliente).
const PADRAO_CLIENTE_UNICO = /\bc\s?0?\d{2,4}\b/i;

/**
 * Devolve { faixa, tendencia } se a pergunta claramente pede a lista de
 * previsão de risco, ou null se não reconhecer o padrão (cai no fallback
 * de IA como antes).
 */
export function detectarPerguntaDeRisco(texto) {
  if (!texto) return null;
  if (PADRAO_CLIENTE_UNICO.test(texto)) return null;
  if (!PALAVRAS_RISCO.test(texto)) return null;

  const filtros = {};
  if (PADRAO_SUBINDO.test(texto)) filtros.tendencia = 'subindo';
  else if (PADRAO_CAINDO.test(texto)) filtros.tendencia = 'caindo';
  else if (PADRAO_ESTAVEL.test(texto)) filtros.tendencia = 'estavel';

  if (PADRAO_CRITICO.test(texto)) filtros.faixa = 'Crítico';
  else if (PADRAO_EM_RISCO.test(texto)) filtros.faixa = 'Em risco';
  else if (PADRAO_ATENCAO.test(texto)) filtros.faixa = 'Atenção';
  else if (PADRAO_SAUDAVEL.test(texto)) filtros.faixa = 'Saudável';

  // Sem "cliente(s)"/"empresa(s)" na frase, só reconhece quando tem uma
  // faixa ou tendência explícita ("Quais estão na faixa 'Em risco'?", um
  // follow-up sugerido pelo próprio widget — ver followUpQuestions.js).
  // "risco" sozinho, sem mais nada, é vago demais (podia ser sobre outra
  // coisa) e continua caindo no fallback de IA.
  if (!PALAVRAS_CLIENTES.test(texto) && !filtros.faixa && !filtros.tendencia) return null;

  return filtros;
}

const ROTULO_TENDENCIA = { subindo: 'subindo', caindo: 'caindo', estavel: 'estável', sem_dado_anterior: 'sem dado anterior' };

function montarTexto(filtros, total) {
  const partes = [];
  if (filtros.faixa) partes.push(`na faixa "${filtros.faixa}"`);
  if (filtros.tendencia) partes.push(`com risco ${ROTULO_TENDENCIA[filtros.tendencia]}`);
  const qualificador = partes.length ? ` ${partes.join(' e ')}` : '';
  if (total === 0) return `Nenhum cliente${qualificador} no momento.`;
  return `${total} cliente${total === 1 ? '' : 's'}${qualificador}, ordenados por probabilidade de cancelamento:`;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000/api';

/**
 * Chama a rota rápida se a pergunta bater o padrão. Retorna null se não
 * bater (deixa quem chamou seguir pro fallback de IA) ou se a rota falhar
 * (backend fora do ar, SQL Server indisponível) — mesmo comportamento de
 * "deixa o próximo nível tentar" do resto do assistenteApi.js.
 */
export async function tentarRiscoDireto(texto) {
  const filtros = detectarPerguntaDeRisco(texto);
  if (!filtros) return null;

  const params = new URLSearchParams({ limite: '20', ...filtros });
  try {
    const controlador = new AbortController();
    const timeoutId = setTimeout(() => controlador.abort(), 6000);
    const resposta = await fetch(`${BACKEND_URL}/risco/previsao?${params}`, { signal: controlador.signal });
    clearTimeout(timeoutId);
    if (!resposta.ok) return null;
    const dados = await resposta.json();
    if (!dados?.clientes) return null;

    const colunas = ['Cliente', 'Probabilidade', 'Faixa', 'Tendência', 'Ação Sugerida'];
    const linhas = dados.clientes.map((c) => ({
      Cliente: c.cliente_id,
      Probabilidade: `${c.risco_percentual.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`,
      Faixa: c.faixa,
      Tendência: ROTULO_TENDENCIA[c.tendencia] ?? c.tendencia,
      'Ação Sugerida': c.acao_sugerida,
    }));

    return {
      texto: montarTexto(filtros, dados.total_clientes),
      colunas,
      linhas,
      contexto: `Mês de referência: ${dados.mes_referencia}. Probabilidade real prevista por modelo de regressão logística treinado (AUC~0.95), não uma nota heurística.${dados.truncado ? ' Lista truncada nos 20 primeiros por probabilidade.' : ''}`,
    };
  } catch {
    return null; // rede caiu, timeout — deixa o fallback de IA tentar
  }
}
