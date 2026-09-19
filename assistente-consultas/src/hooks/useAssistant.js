import { useCallback, useRef, useState } from 'react';
import { interpretarPergunta } from '../engine/matchIntent.js';
import { registrarSugestao } from '../engine/suggestionsStore.js';

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

const SAUDACAO_INICIAL = {
  id: 'msg-saudacao',
  autor: 'assistente',
  payload: { kind: 'text', text: 'Olá! Posso te ajudar a consultar as informações já cadastradas no sistema. O que você gostaria de saber?' },
  criadaEm: new Date().toISOString(),
};

export function useAssistant() {
  const [aberto, setAberto] = useState(false);
  const [bolhaSaudacaoVisivel, setBolhaSaudacaoVisivel] = useState(true);
  const [mensagens, setMensagens] = useState([SAUDACAO_INICIAL]);
  const [status, setStatus] = useState('idle'); // idle | loading | erro
  const pendingTimer = useRef(null);

  const abrir = useCallback(() => {
    setAberto(true);
    setBolhaSaudacaoVisivel(false);
  }, []);

  const fechar = useCallback(() => setAberto(false), []);
  const fecharBolha = useCallback(() => setBolhaSaudacaoVisivel(false), []);

  const enviarPergunta = useCallback((textoBruto) => {
    const texto = textoBruto.trim();
    if (!texto || status === 'loading') return;

    const mensagemUsuario = {
      id: newId(),
      autor: 'usuario',
      texto,
      criadaEm: new Date().toISOString(),
    };
    setMensagens((atual) => [...atual, mensagemUsuario]);
    setStatus('loading');

    // Simula latência real de consulta — mantém o estado "Consultando os
    // registros..." visível o suficiente para não parecer instantâneo/falso.
    pendingTimer.current = setTimeout(() => {
      try {
        const { payload } = interpretarPergunta(texto);
        const mensagemResposta = {
          id: newId(),
          autor: 'assistente',
          payload,
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
    }, 900);
  }, [status]);

  const confirmarSugestao = useCallback((mensagemId) => {
    setMensagens((atual) => {
      const alvo = atual.find((m) => m.id === mensagemId);
      if (alvo?.perguntaOrigem) registrarSugestao(alvo.perguntaOrigem);
      return atual.map((m) => (m.id === mensagemId ? { ...m, sugestaoStatus: 'enviada' } : m));
    });
  }, []);

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
