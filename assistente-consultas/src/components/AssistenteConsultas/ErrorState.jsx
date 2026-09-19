import { ErrorTriangleIcon } from './icons/index.jsx';

// Estado adicional que não estava no protótipo, mas é obrigatório para
// produção (a especificação pede explicitamente esse estado).
export function ErrorState({ onTentarNovamente }) {
  return (
    <div className="ac-message-row">
      <div className="ac-bubble ac-bubble--assistant ac-error">
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <ErrorTriangleIcon />
          <div className="ac-error__text">
            Algo deu errado ao consultar os registros. Tente novamente em instantes.
          </div>
        </div>
        <button type="button" className="ac-btn ac-btn--outline" onClick={onTentarNovamente}>
          Tentar novamente
        </button>
      </div>
    </div>
  );
}
