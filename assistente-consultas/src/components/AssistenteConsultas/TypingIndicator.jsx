import { SparkleIcon } from './icons/index.jsx';

export function TypingIndicator() {
  return (
    <div className="ac-message-row">
      <span className="ac-message-row__avatar">
        <SparkleIcon size={13} color="#FFFFFF" />
      </span>
      <div className="ac-bubble ac-bubble--assistant">
        <div className="ac-typing" role="status" aria-live="off">
          <span className="ac-typing__dot" />
          <span className="ac-typing__dot" />
          <span className="ac-typing__dot" />
        </div>
        <div className="ac-typing__label">Consultando os registros...</div>
      </div>
    </div>
  );
}
