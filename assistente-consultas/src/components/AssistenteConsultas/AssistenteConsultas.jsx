import { useEffect, useRef } from 'react';
import './AssistenteConsultas.css';
import { useAssistant } from '../../hooks/useAssistant.js';
import { obterPerguntasSugeridas } from '../../data/suggestedQuestions.js';
import { FAB } from './FAB.jsx';
import { GreetingBubble } from './GreetingBubble.jsx';
import { PanelHeader } from './PanelHeader.jsx';
import { SuggestedQuestions } from './SuggestedQuestions.jsx';
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
    fecharBolha,
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

            {status === 'loading' && <TypingIndicator />}
            {status === 'erro' && <ErrorState onTentarNovamente={tentarNovamente} />}
          </div>

          <Composer onEnviar={enviarPergunta} desabilitado={status === 'loading'} />
        </div>
      )}

      {!aberto && bolhaSaudacaoVisivel && <GreetingBubble onClose={fecharBolha} onClick={abrir} />}
      {!aberto && <FAB onClick={abrir} />}
    </div>
  );
}
