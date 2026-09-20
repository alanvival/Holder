// Chips de "continuar a conversa" mostrados só depois da ÚLTIMA resposta da
// IA (não em toda mensagem — ficaria poluído) — dá a sensação de diálogo
// contínuo em vez de pergunta-resposta isolada, sem a IA inventar dado
// nenhum: cada chip é só uma pergunta pronta, quem responde de verdade
// continua sendo o mesmo motor de tools.
export function FollowUpQuestions({ perguntas, onSelecionar }) {
  if (!perguntas || perguntas.length === 0) return null;
  return (
    <div className="ac-followups">
      <div className="ac-followups__label">Continuar perguntando</div>
      <div className="ac-followups__chips">
        {perguntas.map((pergunta) => (
          <button
            key={pergunta}
            type="button"
            className="ac-suggestion-chip ac-suggestion-chip--followup"
            onClick={() => onSelecionar(pergunta)}
          >
            {pergunta}
          </button>
        ))}
      </div>
    </div>
  );
}
