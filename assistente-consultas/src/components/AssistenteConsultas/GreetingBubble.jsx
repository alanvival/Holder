import { SparkleIcon, CloseIcon } from './icons/index.jsx';

export function GreetingBubble({ onClose, onClick }) {
  return (
    <div className="ac-greeting" role="note">
      <button type="button" className="ac-greeting__close" onClick={onClose} aria-label="Fechar sugestão">
        <CloseIcon />
      </button>
      <button
        type="button"
        className="ac-greeting__body"
        onClick={onClick}
        style={{ background: 'transparent', border: 'none', padding: 0, textAlign: 'left' }}
      >
        <span className="ac-greeting__avatar">
          <SparkleIcon size={17} color="#FFFFFF" />
        </span>
        <span style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <span className="ac-greeting__title">Assistente de Consultas</span>
          <span className="ac-greeting__text">Oi! Posso te ajudar a encontrar uma informação no sistema. É só perguntar.</span>
        </span>
      </button>
    </div>
  );
}
