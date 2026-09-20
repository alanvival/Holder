import { useEffect, useRef } from 'react';
import './AssistenteConsultas.css';
import { useAssistant } from '../../hooks/useAssistant.js';
import { obterPerguntasSugeridas } from '../../data/suggestedQuestions.js';
import { obterFollowUps } from '../../data/followUpQuestions.js';
import { FAB } from './FAB.jsx';
import { GreetingBubble } from './GreetingBubble.jsx';
import { PanelHeader } from './PanelHeader.jsx';
import { SuggestedQuestions } from './SuggestedQuestions.jsx';
import { FollowUpQuestions } from './FollowUpQuestions.jsx';
import { MessageBubble } from './MessageBubble.jsx';
import { TypingIndicator } from './TypingIndicator.jsx';
import { Composer } from './Composer.jsx';
import { ErrorState } from './ErrorState.jsx';

const perguntasSugeridas = obterPerguntasSugeridas();

export function AssistenteConsultas() {
  const {
    aberto,
    bolhaSaudacaoVisivel,
    mensagens,
    status,
    abrir,
    fechar,
    mostrarBolha,
    ocultarBolhaComAtraso,
    enviarPergunta,
    confirmarSugestao,
    dispensarSugestao,
    tentarNovamente,
  } = useAssistant();

  const bodyRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [mensagens, status]);

  // Sugestões só aparecem quando ainda não há troca de conversa (além da
  // saudação inicial) — depois disso o usuário já está no fluxo de perguntas.
  const mostrarSugestoes = mensagens.length === 1;

  // Follow-ups só na ÚLTIMA mensagem, e só quando ela foi respondida pela
  // IA com sucesso (origem 'catalogo' já é uma resposta fechada/simples,
  // não precisa de "continuar" — e not_found já tem seu próprio prompt de
  // sugestão) — é o que dá a sensação de diálogo contínuo sem poluir toda
  // mensagem antiga com botões desatualizados.
  const ultimaMensagem = mensagens[mensagens.length - 1];
  const mostrarFollowUps =
    status !== 'loading' &&
    ultimaMensagem?.autor === 'assistente' &&
    ultimaMensagem?.origem === 'ia' &&
    ultimaMensagem?.payload?.kind !== 'not_found';

  return (
    <div className="ac-root" data-aberto={aberto}>
      {aberto && (
        <div
          className="ac-panel"
          role="dialog"
          aria-modal="false"
          aria-label="Assistente de Consultas Preditivo"
        >
          <PanelHeader onClose={fechar} />

          <div className="ac-panel__body" ref={bodyRef} aria-live="polite">
            {mensagens.map((mensagem) => (
              <MessageBubble
                key={mensagem.id}
                mensagem={mensagem}
                onConfirmarSugestao={confirmarSugestao}
                onDispensarSugestao={dispensarSugestao}
              />
            ))}

            {mostrarSugestoes && status !== 'loading' && (
              <SuggestedQuestions perguntas={perguntasSugeridas} onSelecionar={enviarPergunta} />
            )}

            {mostrarFollowUps && (
              <FollowUpQuestions perguntas={obterFollowUps(ultimaMensagem.intentId)} onSelecionar={enviarPergunta} />
            )}

            {status === 'loading' && <TypingIndicator />}
            {status === 'erro' && <ErrorState onTentarNovamente={tentarNovamente} />}
          </div>

          <Composer onEnviar={enviarPergunta} desabilitado={status === 'loading'} />
        </div>
      )}

      {!aberto && (
        <div onMouseEnter={mostrarBolha} onMouseLeave={ocultarBolhaComAtraso}>
          {bolhaSaudacaoVisivel && <GreetingBubble onClick={abrir} />}
          <FAB onClick={abrir} />
        </div>
      )}
    </div>
  );
}
