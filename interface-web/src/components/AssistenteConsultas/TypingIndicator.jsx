import { useEffect, useState } from 'react';
import { ChatIcon } from './icons/index.jsx';

// A partir daqui já não é mais "só um instante" — perguntas que caem no
// fallback de IA legitimamente podem levar dezenas de segundos (ver
// TIMEOUT_FALLBACK_IA_MS em assistenteApi.js). Sem nenhum aviso, os três
// pontinhos pulando por 20-40s pareciam a tela travada, não "ainda
// processando" — reportado ao vivo. A partir deste limiar mostra quanto
// tempo já passou e a opção de desistir, em vez de só esperar.
const LIMIAR_AVISO_MS = 6000;

export function TypingIndicator({ onCancelar }) {
  const [decorridoMs, setDecorridoMs] = useState(0);

  useEffect(() => {
    const inicio = Date.now();
    const intervalo = setInterval(() => setDecorridoMs(Date.now() - inicio), 500);
    return () => clearInterval(intervalo);
  }, []);

  const mostrarAviso = decorridoMs >= LIMIAR_AVISO_MS;
  const segundos = Math.floor(decorridoMs / 1000);

  return (
    <div className="ac-message-row">
      <span className="ac-message-row__avatar">
        <ChatIcon size={13} color="#FFFFFF" />
      </span>
      <div className="ac-bubble ac-bubble--assistant">
        <div className="ac-typing" role="status" aria-live="off">
          <span className="ac-typing__dot" />
          <span className="ac-typing__dot" />
          <span className="ac-typing__dot" />
        </div>
        <div className="ac-typing__label">
          {mostrarAviso
            ? `Ainda buscando (${segundos}s) — perguntas fora do catálogo padrão podem levar até 45s...`
            : 'Consultando os registros...'}
        </div>
        {mostrarAviso && onCancelar && (
          <button type="button" className="ac-typing__cancelar" onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}
