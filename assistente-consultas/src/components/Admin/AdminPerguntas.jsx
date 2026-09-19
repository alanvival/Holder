import { useCallback, useEffect, useState } from 'react';
import './AdminPerguntas.css';
import { useTenant } from '../../context/TenantContext.jsx';
import {
  listarPerguntasCadastradas,
  cadastrarPergunta,
  desativarPergunta,
  listarSugestoes,
  aprovarSugestaoUsuario,
  rejeitarSugestaoUsuario,
} from '../../services/assistenteApi.js';

function NovaPerguntaForm({ onCriada }) {
  const tenant = useTenant();
  const [rotulo, setRotulo] = useState('');
  const [exemplos, setExemplos] = useState('');
  const [respostaTexto, setRespostaTexto] = useState('');
  const [enviando, setEnviando] = useState(false);

  const submeter = async (e) => {
    e.preventDefault();
    const listaExemplos = exemplos
      .split('\n')
      .map((linha) => linha.trim())
      .filter(Boolean);
    if (!rotulo.trim() || listaExemplos.length === 0 || !respostaTexto.trim()) return;

    setEnviando(true);
    try {
      await cadastrarPergunta({ rotulo: rotulo.trim(), exemplos: listaExemplos, respostaTexto: respostaTexto.trim() }, tenant);
      setRotulo('');
      setExemplos('');
      setRespostaTexto('');
      onCriada();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="admin-form" onSubmit={submeter}>
      <div className="admin-field">
        <label htmlFor="admin-rotulo">Nome da pergunta-chave</label>
        <input
          id="admin-rotulo"
          type="text"
          value={rotulo}
          onChange={(e) => setRotulo(e.target.value)}
          placeholder="Ex: Prazo de entrega do pedido"
        />
      </div>
      <div className="admin-field">
        <label htmlFor="admin-exemplos">Frases de exemplo (uma por linha)</label>
        <textarea
          id="admin-exemplos"
          value={exemplos}
          onChange={(e) => setExemplos(e.target.value)}
          placeholder={'Qual o prazo de entrega do pedido?\nQuando meu pedido chega?'}
        />
      </div>
      <div className="admin-field">
        <label htmlFor="admin-resposta">Texto de resposta</label>
        <textarea
          id="admin-resposta"
          value={respostaTexto}
          onChange={(e) => setRespostaTexto(e.target.value)}
          placeholder="O que o assistente deve responder quando reconhecer essa pergunta."
        />
      </div>
      <button type="submit" className="admin-btn admin-btn--primary" disabled={enviando} style={{ alignSelf: 'flex-start' }}>
        {enviando ? 'Cadastrando...' : 'Cadastrar pergunta'}
      </button>
    </form>
  );
}

function LinhaSugestao({ sugestao, onAprovar, onRejeitar }) {
  const [expandido, setExpandido] = useState(false);
  const [respostaTexto, setRespostaTexto] = useState('');
  const [processando, setProcessando] = useState(false);

  const confirmarAprovacao = async () => {
    setProcessando(true);
    try {
      await onAprovar(sugestao.id, respostaTexto.trim() || undefined);
    } finally {
      setProcessando(false);
    }
  };

  return (
    <div className="admin-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div className="admin-row__main">
          <div className="admin-row__label">{sugestao.perguntaOriginal}</div>
          <div className="admin-row__meta">
            Sugerida em {new Date(sugestao.criadaEm).toLocaleDateString('pt-BR')}
          </div>
        </div>
        <div className="admin-row__actions">
          <button
            type="button"
            className="admin-btn admin-btn--primary"
            onClick={() => setExpandido((v) => !v)}
          >
            Aprovar
          </button>
          <button
            type="button"
            className="admin-btn admin-btn--danger"
            onClick={() => onRejeitar(sugestao.id)}
          >
            Rejeitar
          </button>
        </div>
      </div>
      {expandido && (
        <div className="admin-approve-inline">
          <textarea
            placeholder="Texto de resposta para essa consulta (opcional — pode configurar depois)"
            value={respostaTexto}
            onChange={(e) => setRespostaTexto(e.target.value)}
            style={{ minHeight: 56 }}
          />
          <button
            type="button"
            className="admin-btn admin-btn--primary"
            style={{ alignSelf: 'flex-start' }}
            onClick={confirmarAprovacao}
            disabled={processando}
          >
            {processando ? 'Confirmando...' : 'Confirmar e cadastrar'}
          </button>
        </div>
      )}
    </div>
  );
}

export function AdminPerguntas() {
  const tenant = useTenant();
  const [perguntas, setPerguntas] = useState([]);
  const [sugestoesPendentes, setSugestoesPendentes] = useState([]);
  const [carregando, setCarregando] = useState(true);

  const recarregar = useCallback(async () => {
    const [listaPerguntas, listaSugestoes] = await Promise.all([
      listarPerguntasCadastradas(tenant),
      listarSugestoes(tenant),
    ]);
    setPerguntas(listaPerguntas);
    setSugestoesPendentes(listaSugestoes.filter((s) => s.status === 'pendente'));
    setCarregando(false);
  }, [tenant]);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  const aprovar = async (id, respostaTexto) => {
    await aprovarSugestaoUsuario(id, { respostaTexto }, tenant);
    await recarregar();
  };

  const rejeitar = async (id) => {
    await rejeitarSugestaoUsuario(id, tenant);
    await recarregar();
  };

  const desativar = async (id) => {
    await desativarPergunta(id, tenant);
    await recarregar();
  };

  if (carregando) {
    return <div className="admin-page">Carregando…</div>;
  }

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">Administração do Assistente</h1>
      <p className="admin-page__subtitle">
        Empresa: {tenant.empresaAtual.nome} · Usuário: {tenant.usuarioAtual.nome}
      </p>

      <section className="admin-section">
        <div className="admin-section__header">
          <h2 className="admin-section__title">Sugestões pendentes dos usuários</h2>
          <span className="admin-section__count">{sugestoesPendentes.length} pendente(s)</span>
        </div>
        {sugestoesPendentes.length === 0 ? (
          <div className="admin-empty">Nenhuma sugestão pendente no momento.</div>
        ) : (
          <div className="admin-list">
            {sugestoesPendentes.map((sugestao) => (
              <LinhaSugestao key={sugestao.id} sugestao={sugestao} onAprovar={aprovar} onRejeitar={rejeitar} />
            ))}
          </div>
        )}
      </section>

      <section className="admin-section">
        <div className="admin-section__header">
          <h2 className="admin-section__title">Perguntas cadastradas</h2>
          <span className="admin-section__count">{perguntas.length} no total</span>
        </div>
        <div className="admin-list">
          {perguntas.map((intent) => (
            <div className="admin-row" key={intent.id}>
              <div className="admin-row__main">
                <div className="admin-row__label">{intent.rotulo}</div>
                <div className="admin-row__meta">
                  <span className={`admin-badge admin-badge--${intent.origem}`}>
                    {intent.origem === 'admin' ? 'Cadastrada pelo admin' : 'Padrão do sistema'}
                  </span>
                  {!intent.ativa && <span className="admin-badge admin-badge--inativa">Inativa</span>}
                  {intent.exemplos.length} frase(s) de exemplo
                </div>
              </div>
              {intent.ativa && (
                <div className="admin-row__actions">
                  <button type="button" className="admin-btn admin-btn--outline" onClick={() => desativar(intent.id)}>
                    Desativar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <NovaPerguntaForm onCriada={recarregar} />
      </section>
    </div>
  );
}
