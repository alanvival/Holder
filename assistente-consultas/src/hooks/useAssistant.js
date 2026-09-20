import { useCallback, useEffect, useState } from 'react';
import { consultarPergunta, registrarSugestaoUsuario, hidratarCatalogoAdmin } from '../services/assistenteApi.js';
import { useTenant } from '../context/TenantContext.jsx';

// Histórico de conversa — estrutura pronta para persistir por usuário depois:
// Mensagem = {
//   id: string,
//   autor: 'usuario' | 'assistente',
//   texto?: string,                 // usada para mensagens do usuário
//   payload?: RespostaPayload,      // usada para respostas estruturadas do assistente
//   perguntaOrigem?: string,        // só em payload.kind === 'not_found': a pergunta que não teve match
//   sugestaoStatus?: 'pendente' | 'enviada' | 'dispensada',
//   criadaEm: string (ISO),
// }

let nextMessageId = 1;
function newId() {
  return `msg-${nextMessageId++}`;
}

// Últimas trocas da conversa, no formato {role, content} que o fallback de
// IA entende (ver fallback_ia/ia_fallback.py) — sem isso, cada pergunta ia
// pro modelo sem NENHUM contexto anterior, então "esse cliente"/"e esse
// outro" nunca resolviam a quem a conversa se referia (bug reportado ao
// vivo). Limitado às últimas 3 trocas (6 mensagens) pra não inflar o custo
// de tokens em conversas longas — o suficiente pra resolver referências
// recentes, não precisa do histórico inteiro da sessão.
const MAX_TROCAS_HISTORICO = 3;

function construirHistoricoParaIa(mensagens) {
  return mensagens
    .filter((m) => m.id !== 'msg-saudacao' && m.payload?.kind !== 'not_found')
    .slice(-MAX_TROCAS_HISTORICO * 2)
    .map((m) => ({
      role: m.autor === 'usuario' ? 'user' : 'assistant',
      content: m.autor === 'usuario' ? m.texto : (m.payload?.text ?? ''),
    }))
    .filter((m) => m.content);
}

const SAUDACAO_INICIAL = {
  id: 'msg-saudacao',
  autor: 'assistente',
  payload: { kind: 'text', text: 'Olá! Posso te ajudar a consultar as informações já cadastradas no sistema, e também prever riscos futuros de cancelamento. O que você gostaria de saber?' },
  criadaEm: new Date().toISOString(),
};

export function useAssistant() {
  const tenant = useTenant();
  const [aberto, setAberto] = useState(false);
  const [bolhaSaudacaoVisivel, setBolhaSaudacaoVisivel] = useState(true);
  const [mensagens, setMensagens] = useState([SAUDACAO_INICIAL]);
  const [status, setStatus] = useState('idle'); // idle | loading | erro

  // Sincroniza as perguntas cadastradas pelo admin (persistidas no
  // backend) pro motor local de matching, uma vez ao montar — assim elas
  // ficam respondíveis mesmo que o usuário nunca abra a tela de Admin.
  useEffect(() => {
    hidratarCatalogoAdmin();
  }, []);

  const abrir = useCallback(() => {
    setAberto(true);
    setBolhaSaudacaoVisivel(false);
  }, []);

  const fechar = useCallback(() => setAberto(false), []);
  const fecharBolha = useCallback(() => setBolhaSaudacaoVisivel(false), []);

  const enviarPergunta = useCallback(async (textoBruto) => {
    const texto = textoBruto.trim();
    if (!texto || status === 'loading') return;

    const mensagemUsuario = {
      id: newId(),
      autor: 'usuario',
      texto,
      criadaEm: new Date().toISOString(),
    };
    // Histórico pra IA construído ANTES de adicionar a pergunta atual na
    // lista — é o contexto que já existia até aqui, a pergunta atual vai
    // separada (parâmetro `pergunta` de responder_com_fallback_ia).
    const historicoParaIa = construirHistoricoParaIa(mensagens);
    setMensagens((atual) => [...atual, mensagemUsuario]);
    setStatus('loading');

    try {
      const inicio = Date.now();
      const { payload, origem, intentId } = await consultarPergunta(texto, { historico: historicoParaIa });

      // O catálogo determinístico resolve em memória (instantâneo) — sem
      // um atraso mínimo, a resposta aparece antes do indicador "digitando"
      // sequer piscar na tela, parecendo um formulário automático em vez de
      // uma conversa. A IA já demora de verdade (chamada de rede), não
      // precisa disso. Delay pequeno e só pra completar até um piso, nunca
      // soma tempo de espera em cima do que já levou.
      const DELAY_MINIMO_MS = 650;
      const decorrido = Date.now() - inicio;
      if (decorrido < DELAY_MINIMO_MS) {
        await new Promise((resolve) => setTimeout(resolve, DELAY_MINIMO_MS - decorrido));
      }

      const mensagemResposta = {
        id: newId(),
        autor: 'assistente',
        payload,
        origem, // 'catalogo' | 'ia' — indicador visual + escolha de follow-ups
        intentId: intentId ?? null, // nome da tool (IA) — escolhe os follow-ups certos
        ...(payload.kind === 'not_found'
          ? { perguntaOrigem: texto, sugestaoStatus: 'pendente' }
          : {}),
        criadaEm: new Date().toISOString(),
      };
      setMensagens((atual) => [...atual, mensagemResposta]);
      setStatus('idle');
    } catch {
      setStatus('erro');
    }
  }, [status, mensagens]);

  const confirmarSugestao = useCallback(async (mensagemId, perguntaOrigem) => {
    // Efeito colateral (chamada de serviço) fica FORA do updater funcional
    // de setState — updaters podem rodar mais de uma vez (StrictMode em
    // dev, ou React reprocessando) e não podem ter side effects impuros.
    if (perguntaOrigem) await registrarSugestaoUsuario(perguntaOrigem, tenant);
    setMensagens((atual) =>
      atual.map((m) => (m.id === mensagemId ? { ...m, sugestaoStatus: 'enviada' } : m)),
    );
  }, [tenant]);

  const dispensarSugestao = useCallback((mensagemId) => {
    setMensagens((atual) =>
      atual.map((m) => (m.id === mensagemId ? { ...m, sugestaoStatus: 'dispensada' } : m)),
    );
  }, []);

  const tentarNovamente = useCallback(() => {
    setStatus('idle');
  }, []);

  return {
    aberto,
    bolhaSaudacaoVisivel,
    mensagens,
    status,
    abrir,
    fechar,
    fecharBolha,
    enviarPergunta,
    confirmarSugestao,
    dispensarSugestao,
    tentarNovamente,
  };
}
