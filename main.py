import os

# Configura a codificação do PostgreSQL para WIN1252 ANTES de importar o psycopg2.
# Isto resolve definitivamente o erro 'utf-8 codec can't decode'!
os.environ["PGCLIENTENCODING"] = "WIN1252"

import psycopg2
from ofxparse import OfxParser

# ==========================================
# Configurações do PostgreSQL
# ==========================================
DB_HOST = "localhost"
DB_NAME = "projeto_ofx"      # Nome da base de dados
DB_USER = "postgres"         # Utilizador padrão
DB_PASS = os.getenv("DB_PASS")
DB_PORT = "5432"

caminho_arquivo = "extrato.ofx"

if not os.path.exists(caminho_arquivo):
    print(f"❌ Ficheiro '{caminho_arquivo}' não encontrado.")
else:
    # 1. Leitura do ficheiro OFX
    with open(caminho_arquivo, "rb") as arquivo:
        ofx = OfxParser.parse(arquivo)

    transacoes = ofx.account.statement.transactions

    entradas = 0.0
    saidas = 0.0

    print("==========================================")
    print("          EXTRATO BANCÁRIO DETALHADO      ")
    print("==========================================")

    for t in transacoes:
        data_fmt = t.date.strftime('%d/%m/%Y')
        valor = float(t.amount)
        descricao = t.memo

        if valor > 0:
            entradas += valor
        else:
            saidas += valor

        print(f"Data      : {data_fmt}")
        print(f"Valor     : R$ {valor:.2f}")
        print(f"Descrição : {descricao}")
        print("------------------------------------------")

    saldo = entradas + saidas

    print("\n==========================================")
    print("               RESUMO FINANCEIRO          ")
    print("==========================================")
    print(f"Total de movimentações : {len(transacoes)}")
    print(f"Total de entradas      : R$ {entradas:.2f}")
    print(f"Total de saídas        : R$ {saidas:.2f}")
    print(f"Saldo calculado        : R$ {saldo:.2f}")
    print("==========================================")

    # 2. Integração com PostgreSQL (Criação Automática do Banco e da Tabela)
    try:
        # Liga à base de dados padrão 'postgres' para verificar/criar a 'projeto_ofx'
        conn_admin = psycopg2.connect(
            host=DB_HOST,
            database="postgres",
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        conn_admin.autocommit = True
        cursor_admin = conn_admin.cursor()

        # Cria a base de dados projeto_ofx caso ainda não exista
        cursor_admin.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (DB_NAME,))
        if not cursor_admin.fetchone():
            cursor_admin.execute(f'CREATE DATABASE "{DB_NAME}";')
            print(f"✨ Base de dados '{DB_NAME}' criada automaticamente!")

        cursor_admin.close()
        conn_admin.close()

        # Liga à base de dados 'projeto_ofx'
        conexao = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        cursor = conexao.cursor()

        # Cria a tabela automaticamente se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id SERIAL PRIMARY KEY,
                data_movimentacao DATE,
                valor NUMERIC(15,2),
                descricao VARCHAR(255),
                fitid VARCHAR(255) UNIQUE
            );
        """)

        query = """
        INSERT INTO movimentacoes (data_movimentacao, valor, descricao, fitid)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (fitid) DO NOTHING;
        """

        inseridos = 0
        for t in transacoes:
            cursor.execute(query, (t.date, t.amount, t.memo, t.id))
            if cursor.rowcount > 0:
                inseridos += 1

        conexao.commit()
        cursor.close()
        conexao.close()

        print("\n💾 POSTGRESQL:")
        print(f"   • {inseridos} novos registos inseridos com sucesso!")
        print("==========================================\n")

    except Exception as e:
        print(f"\n❌ Erro ao operar no PostgreSQL:\n{e}\n")