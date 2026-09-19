import streamlit as st

from api_client import ApiErro
from auth import barra_lateral_usuario, cliente_api, esta_logado, iniciar_sessao

st.set_page_config(page_title="Holder · Retenção de clientes", layout="centered")
st.title("Holder — Fila de retenção de clientes")

if esta_logado():
    barra_lateral_usuario()
    usuario = st.session_state["usuario"]
    st.success(f"Você está conectado como **{usuario['usuario']}**.")
    st.markdown(
        "Use o menu lateral para abrir o **Dashboard** (com quem falar, por quê e em que ordem), "
        "a lista de **Clientes** ou a **Análise mensal**."
    )
    st.stop()

aba_entrar, aba_cadastrar = st.tabs(["Entrar", "Criar conta"])

with aba_entrar:
    with st.form("form_login"):
        usuario = st.text_input("Usuário", key="login_usuario")
        senha = st.text_input("Senha", type="password", key="login_senha")
        entrar = st.form_submit_button("Entrar", type="primary", key="botao_entrar")
    if entrar:
        resposta = None
        if not usuario or not senha:
            st.error("Informe usuário e senha.")
        else:
            try:
                resposta = cliente_api().login(usuario, senha)
            except ApiErro as erro:
                st.error(erro.detail)
        if resposta:
            iniciar_sessao(resposta)
            st.rerun()

with aba_cadastrar:
    with st.form("form_cadastro"):
        nome = st.text_input("Nome completo", key="cadastro_nome")
        novo_usuario = st.text_input(
            "Usuário",
            key="cadastro_usuario",
            help="3 a 50 caracteres: letras, números, ponto, hífen ou sublinhado.",
        )
        nova_senha = st.text_input(
            "Senha",
            type="password",
            key="cadastro_senha",
            help="8 a 128 caracteres, com ao menos uma letra e um número.",
        )
        confirmacao = st.text_input("Confirme a senha", type="password", key="cadastro_confirmacao")
        cadastrar = st.form_submit_button("Criar conta", type="primary", key="botao_cadastrar")
    if cadastrar:
        resposta = None
        if nova_senha != confirmacao:
            st.error("As senhas não conferem.")
        else:
            try:
                api = cliente_api()
                api.cadastrar(nome, novo_usuario, nova_senha)
                resposta = api.login(novo_usuario, nova_senha)
            except ApiErro as erro:
                st.error(erro.detail)
        if resposta:
            iniciar_sessao(resposta)
            st.rerun()
