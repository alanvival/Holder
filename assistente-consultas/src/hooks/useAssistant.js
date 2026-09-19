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

const SAUDACAO_INICIAL = {
  id: 'msg-saudacao',
  autor: 'assistente',
  payload: { kind: 'text', text: 'Olá! Posso te ajudar a consultar as informações já cadastradas no sistema. O que você gostaria de saber?' },
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
    setMensagens((atual) => [...atual, mensagemUsuario]);
    setStatus('loading');

    try {
      const { payload, origem } = await consultarPergunta(texto, tenant);
      const mensagemResposta = {
        id: newId(),
        autor: 'assistente',
        payload,
        origem, // 'catalogo' | 'ia' — usado só pra um indicador visual sutil
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
  }, [status, tenant]);

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
