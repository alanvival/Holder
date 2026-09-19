"""Sessão do usuário no Streamlit: o JWT fica em st.session_state."""

from collections.abc import Callable

import streamlit as st

from api_client import ApiClient, ApiErro, NaoAutenticado

CHAVE_TOKEN = "token"
CHAVE_USUARIO = "usuario"

# Ponto de injeção para testes: fábrica do cliente da API.
fabrica_cliente: Callable[..., ApiClient] = ApiClient


def cliente_api() -> ApiClient:
    return fabrica_cliente(token=st.session_state.get(CHAVE_TOKEN))


def esta_logado() -> bool:
    return bool(st.session_state.get(CHAVE_TOKEN))


def iniciar_sessao(resposta_login: dict) -> None:
    st.session_state[CHAVE_TOKEN] = resposta_login["access_token"]
    st.session_state[CHAVE_USUARIO] = resposta_login["usuario"]


def encerrar_sessao() -> None:
    for chave in (CHAVE_TOKEN, CHAVE_USUARIO):
        st.session_state.pop(chave, None)


def barra_lateral_usuario() -> None:
    usuario = st.session_state.get(CHAVE_USUARIO) or {}
    st.sidebar.markdown(f"Olá, **{usuario.get('nome_completo', '')}**")
    if st.sidebar.button("Sair", key="botao_sair"):
        encerrar_sessao()
        st.rerun()


def exigir_login() -> ApiClient:
    """Use no topo de cada página protegida (depois de st.set_page_config)."""
    if not esta_logado():
        st.warning("Faça login na página inicial (Home) para acessar esta página.")
        st.stop()
    barra_lateral_usuario()
    return cliente_api()


def tratar_erro(erro: ApiErro) -> None:
    """Mostra o erro da API e interrompe a página. Sessão expirada → desloga."""
    if isinstance(erro, NaoAutenticado):
        encerrar_sessao()
        st.warning("Sua sessão expirou. Faça login novamente na página inicial (Home).")
    else:
        st.error(erro.detail)
    st.stop()
