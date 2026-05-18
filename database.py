import os
import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não encontrada no ambiente.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    user_id TEXT PRIMARY KEY,
                    nome TEXT,
                    idade INTEGER,
                    cidade TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS idade INTEGER;")
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cidade TEXT;")
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS mensagens (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS memorias (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    chave TEXT NOT NULL,
                    valor TEXT NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chave)
                );
            """)


def salvar_usuario(user_id, nome=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (user_id, nome, atualizado_em)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    nome = COALESCE(EXCLUDED.nome, usuarios.nome),
                    atualizado_em = CURRENT_TIMESTAMP;
            """, (user_id, nome))


def buscar_usuario(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, nome, idade, cidade
                FROM usuarios
                WHERE user_id = %s;
            """, (user_id,))
            return cur.fetchone()


def atualizar_usuario(user_id, nome=None, idade=None, cidade=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE usuarios
                SET
                    nome = COALESCE(%s, nome),
                    idade = COALESCE(%s, idade),
                    cidade = COALESCE(%s, cidade),
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE user_id = %s;
            """, (nome, idade, cidade, user_id))


def salvar_mensagem(user_id, role, content):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mensagens (user_id, role, content)
                VALUES (%s, %s, %s);
            """, (user_id, role, content))


def buscar_historico(user_id, limite=12):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content
                FROM mensagens
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s;
            """, (user_id, limite))
            rows = cur.fetchall()

    rows.reverse()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def salvar_memoria(user_id, chave, valor):
    if not chave or not valor:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memorias (user_id, chave, valor, atualizado_em)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, chave)
                DO UPDATE SET
                    valor = EXCLUDED.valor,
                    atualizado_em = CURRENT_TIMESTAMP;
            """, (user_id, chave, valor))


def buscar_memorias(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chave, valor
                FROM memorias
                WHERE user_id = %s
                ORDER BY atualizado_em DESC;
            """, (user_id,))
            rows = cur.fetchall()

    return {row["chave"]: row["valor"] for row in rows}