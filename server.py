"""
Backend do fallback de IA do Assistente de Consultas.

O catálogo determinístico (assistente-consultas/src/engine/*.js) continua
rodando 100% no navegador — rápido, sem custo, sem chamar isto. Este
servidor só existe pra guardar a ANTHROPIC_API_KEY fora do bundle do front:
quando o catálogo local não reconhece uma pergunta, o widget chama
POST /api/fallback-ia, que roda o fluxo de tool use descrito no prompt de
fallback (fallback_ia/claude_fallback.py).

Rodar:
    cp .env.example .env   # preencher ANTHROPIC_API_KEY
    pip install -r requirements.txt
    python server.py
Escuta em http://localhost:8000 por padrão.
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

from fallback_ia.claude_fallback import responder_com_fallback_ia  # noqa: E402
from fallback_ia.guardrails import limite_excedido  # noqa: E402

app = Flask(__name__)
CORS(app, origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5183")])


@app.post("/api/fallback-ia")
def fallback_ia():
    corpo = request.get_json(silent=True) or {}
    pergunta = (corpo.get("pergunta") or "").strip()
    sessao_id = corpo.get("sessaoId") or request.remote_addr or "anonimo"

    if not pergunta:
        return jsonify({"erro": "Campo 'pergunta' é obrigatório."}), 400

    if limite_excedido(sessao_id):
        return jsonify({"origem": "ia", "encontrado": False, "erro": "rate_limit"}), 429

    resultado = responder_com_fallback_ia(pergunta)
    return jsonify(resultado)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "chave_configurada": bool(os.environ.get("ANTHROPIC_API_KEY"))})


if __name__ == "__main__":
    app.run(port=8000, debug=True)
