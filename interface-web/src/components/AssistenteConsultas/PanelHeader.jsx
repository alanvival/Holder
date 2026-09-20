import { ChatIcon, ChevronDownIcon } from './icons/index.jsx';

export function PanelHeader({ onClose }) {
  return (
    <div className="ac-panel__header">
      <div className="ac-panel__header-left">
        <span className="ac-panel__avatar">
          <ChatIcon size={18} color="#FFFFFF" />
        </span>
        <span>
          <div className="ac-panel__title">Assistente de Consultas Preditivo</div>
          <div className="ac-panel__subtitle">Pergunte sobre seus dados e previsões</div>
        </span>
      </div>
      <button type="button" className="ac-panel__close" onClick={onClose} aria-label="Minimizar">
        <ChevronDownIcon />
      </button>
    </div>
  );
}
