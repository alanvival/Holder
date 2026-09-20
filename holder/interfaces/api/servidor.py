"""
Backend do Assistente de Consultas.

Duas responsabilidades:
1. Fallback de IA — o catálogo determinístico (interface-web/src/
   engine/*.js) continua rodando 100% no navegador; só quando ele não
   reconhece uma pergunta o widget chama POST /api/fallback-ia, que roda o
   fluxo de tool use (holder/aplicacao/assistente/ia_fallback.py, via
   Groq). Existe só pra manter a GROQ_API_KEY fora do bundle do front.
2. Persistência das perguntas cadastradas pelo admin e das sugestões dos
   usuários (holder/infra/persistencia/admin_sqlite.py) — antes viviam só
   em memória no navegador e sumiam a cada refresh.

Rodar:
    cp .env.example .env   # preencher GROQ_API_KEY
    pip install -r requirements.txt
    python -m holder.interfaces.api
Escuta em http://localhost:8000 por padrão.
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

from holder.aplicacao.assistente.ia_fallback import responder_com_fallback_ia  # noqa: E402
from holder.aplicacao.assistente import previsao_risco  # noqa: E402
from holder.infra.ia.guardrails import limite_excedido  # noqa: E402
from holder.infra.persistencia import admin_sqlite as armazenamento  # noqa: E402

app = Flask(__name__)
CORS(app, origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")])

# Cria as tabelas do SQLite se ainda não existirem. Isso era feito no import
# do módulo de persistência, o que fazia qualquer importador — inclusive a
# suíte de testes — abrir conexão e rodar DDL sem pedir. Agora quem precisa
# do banco é quem o inicializa: o servidor.
armazenamento.inicializar()


@app.post("/api/fallback-ia")
def fallback_ia():
    corpo = request.get_json(silent=True) or {}
    pergunta = (corpo.get("pergunta") or "").strip()
    sessao_id = corpo.get("sessaoId") or request.remote_addr or "anonimo"
    # Últimas trocas da conversa (ver useAssistant.js#construirHistoricoParaIa)
    # — sem isso, cada pergunta chegava sem nenhum contexto anterior, e
    # referências tipo "esse cliente"/"e esse outro" nunca resolviam a
    # ninguém (bug reportado ao vivo pelo usuário).
    historico = corpo.get("historico") or []

    if not pergunta:
        return jsonify({"erro": "Campo 'pergunta' é obrigatório."}), 400

    if limite_excedido(sessao_id):
        return jsonify({"origem": "ia", "encontrado": False, "erro": "rate_limit"}), 429

    resultado = responder_com_fallback_ia(pergunta, historico=historico)
    return jsonify(resultado)


@app.get("/api/historico")
def listar_historico():
    """Histórico de conversas (catálogo + IA) já respondidas no widget —
    exibido no painel de Administração pra nada se perder entre sessões."""
    limite = request.args.get("limite", default=100, type=int)
    return jsonify(armazenamento.listar_historico(limite))


@app.post("/api/historico")
def registrar_historico():
    """Chamado pelo front (services/assistenteApi.js) logo depois de
    QUALQUER pergunta respondida — catálogo determinístico ou IA — pra
    ficar tudo no mesmo lugar, não só as chamadas de fallback."""
    corpo = request.get_json(silent=True) or {}
    pergunta = (corpo.get("pergunta") or "").strip()
    if not pergunta:
        return jsonify({"erro": "Campo 'pergunta' é obrigatório."}), 400
    entrada = armazenamento.registrar_conversa(
        pergunta=pergunta,
        resposta=corpo.get("resposta"),
        origem=corpo.get("origem") or "catalogo",
        tool=corpo.get("tool"),
        sucesso=bool(corpo.get("sucesso", True)),
    )
    return jsonify(entrada), 201


@app.get("/api/risco/previsao")
def previsao_risco_rapida():
    """
    Atalho DETERMINÍSTICO (sem Groq) pra família de perguntas sobre
    previsão de risco — faixa, tendência (subindo/caindo/estável). Mesmo
    dado que listar_previsao_risco expõe pra IA, mas direto: o Score de
    Risco já é uma consulta simples ao histórico persistido (fScoreRisco),
    nunca precisou de um modelo de linguagem pra ser respondida.
    Existia só via fallback de IA antes — perguntas como "quais clientes
    estão com risco subindo" dependiam do Groq escolher a tool certa E
    responder dentro do timeout (observado ao vivo levando 30-105s,
    estourando o timeout do front e caindo em "não encontrei" mesmo com o
    dado pronto e rápido de buscar). Ver riscoDireto.js no front, que casa
    o padrão da pergunta com esta rota antes de cair no fallback de IA.
    """
    filtros = {}
    faixa = request.args.get("faixa")
    if faixa:
        filtros["faixa"] = faixa
    tendencia = request.args.get("tendencia")
    if tendencia:
        filtros["tendencia"] = tendencia
    limite = request.args.get("limite", default=20, type=int)
    resultado = previsao_risco.listar_previsao_risco(filtros, limite)
    if "erro" in resultado:
        return jsonify(resultado), 503
    return jsonify(resultado)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "chave_configurada": bool(os.environ.get("GROQ_API_KEY"))})


# --- Perguntas cadastradas pelo admin -------------------------------------

@app.get("/api/perguntas")
def listar_perguntas():
    return jsonify(armazenamento.listar_perguntas_admin())


@app.post("/api/perguntas")
def criar_pergunta():
    corpo = request.get_json(silent=True) or {}
    rotulo = (corpo.get("rotulo") or "").strip()
    exemplos = [e.strip() for e in (corpo.get("exemplos") or []) if e and e.strip()]
    resposta_texto = (corpo.get("respostaTexto") or "").strip()

    if not rotulo or not exemplos or not resposta_texto:
        return jsonify({"erro": "rotulo, exemplos (não vazio) e respostaTexto são obrigatórios."}), 400

    pergunta = armazenamento.criar_pergunta_admin(rotulo, exemplos, resposta_texto)
    return jsonify(pergunta), 201


@app.patch("/api/perguntas/<pergunta_id>")
def atualizar_pergunta(pergunta_id):
    corpo = request.get_json(silent=True) or {}
    if corpo.get("ativa") is False:
        encontrada = armazenamento.desativar_pergunta_admin(pergunta_id)
        if not encontrada:
            return jsonify({"erro": "Pergunta não encontrada."}), 404
        return jsonify({"id": pergunta_id, "ativa": False})
    return jsonify({"erro": "Só suporta desativar (ativa: false) por enquanto."}), 400


# --- Sugestões dos usuários -------------------------------------------------

@app.get("/api/sugestoes")
def listar_sugestoes():
    status = request.args.get("status")
    return jsonify(armazenamento.listar_sugestoes(status))


@app.post("/api/sugestoes")
def criar_sugestao():
    corpo = request.get_json(silent=True) or {}
    pergunta_original = (corpo.get("perguntaOriginal") or "").strip()
    if not pergunta_original:
        return jsonify({"erro": "Campo 'perguntaOriginal' é obrigatório."}), 400
    return jsonify(armazenamento.criar_sugestao(pergunta_original)), 201


@app.post("/api/sugestoes/<sugestao_id>/sugerir-resposta")
def sugerir_resposta(sugestao_id):
    """
    Chamado quando o admin clica em "Aprovar" — pede pra Claude sugerir um
    texto de resposta pra essa sugestão, usando o MESMO fluxo de tool use
    do fallback (nunca inventa número, só formata em cima do resultado real
    de consultar_metrica/buscar_campo_cliente). O admin ainda revisa e
    pode editar antes de confirmar o cadastro — isso aqui só pré-preenche.
    """
    sugestao = armazenamento.buscar_sugestao(sugestao_id)
    if sugestao is None:
        return jsonify({"erro": "Sugestão não encontrada."}), 404

    sessao_id = request.remote_addr or "anonimo"
    if limite_excedido(sessao_id):
        return jsonify({"origem": "ia", "encontrado": False, "erro": "rate_limit"}), 429

    resultado = responder_com_fallback_ia(sugestao["perguntaOriginal"])
    return jsonify(resultado)


@app.post("/api/sugestoes/<sugestao_id>/aprovar")
def aprovar_sugestao(sugestao_id):
    corpo = request.get_json(silent=True) or {}
    resposta_texto = corpo.get("respostaTexto")
    pergunta_criada = armazenamento.aprovar_sugestao(sugestao_id, resposta_texto)
    if pergunta_criada is None:
        return jsonify({"erro": "Sugestão não encontrada ou já processada."}), 404
    return jsonify(pergunta_criada)


@app.post("/api/sugestoes/<sugestao_id>/rejeitar")
def rejeitar_sugestao(sugestao_id):
    encontrada = armazenamento.rejeitar_sugestao(sugestao_id)
    if not encontrada:
        return jsonify({"erro": "Sugestão não encontrada ou já processada."}), 404
    return jsonify({"id": sugestao_id, "status": "rejeitada"})


def main() -> None:
    # threaded=True é o ponto principal deste fix, não um detalhe de
    # performance: o servidor de dev do Flask é single-thread por padrão —
    # UMA chamada lenta ao Groq (observado ao vivo levando 30-150s) travava
    # o processo inteiro, inclusive rotas rápidas e determinísticas sem
    # nenhuma relação com IA (ex: /api/risco/previsao, /api/perguntas).
    # Confirmado ao vivo: sem isso, um fetch direto no navegador pra uma
    # rota que responde em <1s via curl ficava pendurado por dezenas de
    # segundos sempre que havia uma pergunta de IA em voo ao mesmo tempo.
    app.run(port=8000, debug=True, threaded=True)


if __name__ == "__main__":
    main()
