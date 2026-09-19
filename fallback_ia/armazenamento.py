"""
Persistência real (SQLite) das perguntas cadastradas pelo admin e das
sugestões dos usuários — antes viviam só em memória no JS do navegador
(intentRegistry.js / suggestionsStore.js), então cada aba tinha sua própria
cópia e tudo sumia num refresh. Isso passa a ser a fonte de verdade; o
front sincroniza com esses endpoints (ver server.py) e mantém o
comportamento local só como fallback quando o backend está fora do ar.

Só o que precisa de persistência mora aqui: as intenções "de sistema"
(catálogo/métricas com resolver em código) continuam definidas no próprio
código, em JS e Python — não fazem sentido guardadas em banco.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "dados_admin.sqlite3"


@contextmanager
def _conexao():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar():
    with _conexao() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS perguntas_admin (
                id TEXT PRIMARY KEY,
                rotulo TEXT NOT NULL,
                exemplos TEXT NOT NULL,
                resposta_texto TEXT NOT NULL,
                ativa INTEGER NOT NULL DEFAULT 1,
                criada_em TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sugestoes (
                id TEXT PRIMARY KEY,
                pergunta_original TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                criada_em TEXT NOT NULL
            )
            """
        )


def _agora():
    return datetime.now(timezone.utc).isoformat()


def _novo_id(prefixo):
    return f"{prefixo}-{uuid.uuid4().hex[:10]}"


def _pergunta_para_dict(row):
    return {
        "id": row["id"],
        "rotulo": row["rotulo"],
        "exemplos": json.loads(row["exemplos"]),
        "respostaTexto": row["resposta_texto"],
        "ativa": bool(row["ativa"]),
        "criadaEm": row["criada_em"],
        "origem": "admin",
    }


def _sugestao_para_dict(row):
    return {
        "id": row["id"],
        "perguntaOriginal": row["pergunta_original"],
        "status": row["status"],
        "criadaEm": row["criada_em"],
    }


# --- Perguntas cadastradas pelo admin ------------------------------------

def listar_perguntas_admin():
    with _conexao() as conn:
        rows = conn.execute("SELECT * FROM perguntas_admin ORDER BY criada_em").fetchall()
    return [_pergunta_para_dict(r) for r in rows]


def criar_pergunta_admin(rotulo: str, exemplos: list[str], resposta_texto: str) -> dict:
    pergunta = {
        "id": _novo_id("intent-admin"),
        "rotulo": rotulo,
        "exemplos": exemplos,
        "resposta_texto": resposta_texto,
        "ativa": 1,
        "criada_em": _agora(),
    }
    with _conexao() as conn:
        conn.execute(
            "INSERT INTO perguntas_admin (id, rotulo, exemplos, resposta_texto, ativa, criada_em) VALUES (?, ?, ?, ?, ?, ?)",
            (pergunta["id"], rotulo, json.dumps(exemplos, ensure_ascii=False), resposta_texto, 1, pergunta["criada_em"]),
        )
    return {
        "id": pergunta["id"],
        "rotulo": rotulo,
        "exemplos": exemplos,
        "respostaTexto": resposta_texto,
        "ativa": True,
        "criadaEm": pergunta["criada_em"],
        "origem": "admin",
    }


def desativar_pergunta_admin(pergunta_id: str) -> bool:
    with _conexao() as conn:
        cur = conn.execute("UPDATE perguntas_admin SET ativa = 0 WHERE id = ?", (pergunta_id,))
    return cur.rowcount > 0


# --- Sugestões dos usuários ------------------------------------------------

def buscar_sugestao(sugestao_id: str) -> dict | None:
    with _conexao() as conn:
        row = conn.execute("SELECT * FROM sugestoes WHERE id = ?", (sugestao_id,)).fetchone()
    return _sugestao_para_dict(row) if row else None


def listar_sugestoes(status: str | None = None):
    with _conexao() as conn:
        if status:
            rows = conn.execute("SELECT * FROM sugestoes WHERE status = ? ORDER BY criada_em", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sugestoes ORDER BY criada_em").fetchall()
    return [_sugestao_para_dict(r) for r in rows]


def criar_sugestao(pergunta_original: str) -> dict:
    sugestao_id = _novo_id("sug")
    criada_em = _agora()
    with _conexao() as conn:
        conn.execute(
            "INSERT INTO sugestoes (id, pergunta_original, status, criada_em) VALUES (?, ?, 'pendente', ?)",
            (sugestao_id, pergunta_original, criada_em),
        )
    return {"id": sugestao_id, "perguntaOriginal": pergunta_original, "status": "pendente", "criadaEm": criada_em}


def aprovar_sugestao(sugestao_id: str, resposta_texto: str | None = None) -> dict | None:
    """Aprovar transforma a sugestão numa pergunta cadastrada de verdade —
    mesma regra que já existia no store em memória (JS), só que persistida."""
    with _conexao() as conn:
        row = conn.execute("SELECT * FROM sugestoes WHERE id = ? AND status = 'pendente'", (sugestao_id,)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE sugestoes SET status = 'aprovada' WHERE id = ?", (sugestao_id,))

    pergunta_original = row["pergunta_original"]
    return criar_pergunta_admin(
        rotulo=pergunta_original,
        exemplos=[pergunta_original],
        resposta_texto=resposta_texto or "Consulta cadastrada — resposta ainda não configurada pelo administrador.",
    )


def rejeitar_sugestao(sugestao_id: str) -> bool:
    with _conexao() as conn:
        cur = conn.execute("UPDATE sugestoes SET status = 'rejeitada' WHERE id = ? AND status = 'pendente'", (sugestao_id,))
    return cur.rowcount > 0


inicializar()
