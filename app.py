# OBS: Este script requer que o pacote 'streamlit' esteja instalado no seu ambiente.
# Instale com: pip install streamlit openpyxl pandas

from sqlalchemy import create_engine, text
from io import BytesIO
import pandas as pd
from datetime import datetime
import hashlib
import streamlit as st


# Conexão com o banco SQLite
engine = create_engine("sqlite:///gastos.db", echo=False)

# Cria tabela se não existir
with engine.connect() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        categoria TEXT,
        descricao TEXT,
        quantidade REAL,
        unidade TEXT,
        valor_unitario REAL,
        valor_total REAL,
        forma_pagamento TEXT,
        observacoes TEXT
    )
    """))


# ----- Usuários simulados -----
USERS = {
    "admin": hashlib.sha256("1234".encode()).hexdigest(),
    "user": hashlib.sha256("senha".encode()).hexdigest()
}

# ----- Funções auxiliares -----
def check_login(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return USERS.get(username) == hashed

def init_session():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "data" not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=[
            "Data", "Categoria", "Descrição", "Quantidade", "Unidade", 
            "Valor Unitário (R$)", "Valor Total (R$)", "Forma de Pagamento", "Observações"])

# ----- Login -----
def login_screen():
    st.markdown("## 🔐 Login - Sistema de Gastos da Malharia")
    st.markdown("Acesse com seu usuário e senha para continuar.")
    username = st.text_input("👤 Usuário")
    password = st.text_input("🔒 Senha", type="password")
    if st.button("🚪 Entrar"):
        if check_login(username, password):
            st.session_state.authenticated = True
        else:
            st.error("❌ Usuário ou senha incorretos.")

# ----- Cadastro de gastos -----
def register_expense():
    st.markdown("## 📝 Registrar novo gasto")
    with st.form("form_gasto"):
        col1, col2 = st.columns(2)
        data = col1.date_input("📅 Data", value=datetime.today())
        categoria = col2.selectbox("📂 Categoria", [
            "Matéria-prima", "Mão de obra", "Energia elétrica", 
            "Manutenção de máquinas", "Embalagens", "Transporte", "Despesas administrativas"])

        descricao = st.text_input("📝 Descrição")
        col1, col2 = st.columns(2)
        quantidade = col1.number_input("🔢 Quantidade", min_value=1.0)
        unidade = col2.selectbox("📏 Unidade", ["Kg", "und", "mês"])

        col1, col2 = st.columns(2)
        valor_unit = col1.number_input("💲 Valor Unitário (R$)", min_value=0.0)
        valor_total = quantidade * valor_unit
        col2.markdown(f"**💰 Valor Total:** R$ {valor_total:.2f}")

        forma_pagamento = st.selectbox("💳 Forma de Pagamento", ["PIX", "Boleto", "Cartão", "Débito automático", "Dinheiro"])
        obs = st.text_input("🗒️ Observações")

        submitted = st.form_submit_button("💾 Salvar gasto")
        if submitted:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO gastos (data, categoria, descricao, quantidade, unidade,
                                        valor_unitario, valor_total, forma_pagamento, observacoes)
                    VALUES (:data, :categoria, :descricao, :quantidade, :unidade,
                            :valor_unitario, :valor_total, :forma_pagamento, :observacoes)
                """), {
                    "data": data.strftime("%d/%m/%Y"),
                    "categoria": categoria,
                    "descricao": descricao,
                    "quantidade": quantidade,
                    "unidade": unidade,
                    "valor_unitario": valor_unit,
                    "valor_total": valor_total,
                    "forma_pagamento": forma_pagamento,
                    "observacoes": obs
                })
            st.success("✅ Gasto registrado com sucesso!")

# ----- Dashboard -----
def dashboard():
    st.markdown("## 📊 Dashboard de Gastos")
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM gastos", conn)
    if df.empty:
        st.info("ℹ️ Nenhum gasto registrado ainda.")
        return

    st.markdown("### 📋 Tabela de Gastos")
    st.dataframe(df, use_container_width=True)
    st.divider()

    st.markdown("### 📈 Gastos por Categoria")
    gastos_categoria = df.groupby("Categoria")["Valor Total (R$)"].sum()
    st.bar_chart(gastos_categoria)

    st.markdown("### 📅 Evolução Diária dos Gastos")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y")
    gastos_dia = df.groupby("Data")["Valor Total (R$)"].sum()
    st.line_chart(gastos_dia)

    st.divider()
    st.markdown("### 📥 Baixar Planilha Excel")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    data = output.getvalue()

    st.download_button(
        label="⬇️ Baixar gastos em Excel",
        data=data,
        file_name="gastos_malharia.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ----- Main App -----
def main():
    init_session()
    if not st.session_state.authenticated:
        login_screen()
    else:
        st.sidebar.title("📂 Menu")
        op = st.sidebar.radio("Navegar para:", ["Registrar Gasto", "Dashboard", "Sair"])
        if op == "Registrar Gasto":
            register_expense()
        elif op == "Dashboard":
            dashboard()
        elif op == "Sair":
            st.session_state.authenticated = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
