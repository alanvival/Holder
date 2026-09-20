import { ChatIcon } from './icons/index.jsx';

// Tooltip de hover no FAB, no mesmo espírito do widget da Globalsys no site
// institucional: aparece com o mouse em cima, some sozinha ao tirar (ver
// ocultarBolhaComAtraso em useAssistant.js) — sem botão de fechar, porque
// não é uma notificação que precisa de confirmação, é só um rótulo.
export function GreetingBubble({ onClick }) {
  return (
    <button type="button" className="ac-greeting" onClick={onClick} aria-label="Abrir assistente de consultas">
      <span className="ac-greeting__avatar">
        <ChatIcon size={17} color="#FFFFFF" />
      </span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <span className="ac-greeting__title">Assistente de Consultas Preditivo</span>
        <span className="ac-greeting__text">Oi! Posso te ajudar a encontrar uma informação no sistema. É só perguntar.</span>
      </span>
    </button>
  );
}
