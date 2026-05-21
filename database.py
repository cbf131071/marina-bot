import os
import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.environ.get("DATABASE_URL")


ONLINE_MINUTOS = 3
RECENTE_MINUTOS = 15


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


# ============================================================
# FUNÇÕES DO DASHBOARD ADMIN
# ============================================================

def _status_por_minutos(minutos):
    if minutos is None:
        return "offline"
    if minutos <= ONLINE_MINUTOS:
        return "online"
    if minutos <= RECENTE_MINUTOS:
        return "recente"
    return "offline"


def buscar_metricas_admin():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM usuarios) AS total_usuarios,
                    (SELECT COUNT(*) FROM mensagens) AS total_mensagens,
                    (SELECT COUNT(*) FROM memorias) AS total_memorias,
                    (SELECT COUNT(*) FROM mensagens WHERE criado_em::date = CURRENT_DATE) AS mensagens_hoje,
                    (SELECT COUNT(DISTINCT user_id) FROM mensagens WHERE criado_em::date = CURRENT_DATE) AS usuarios_hoje,
                    (SELECT COUNT(DISTINCT user_id) FROM mensagens WHERE criado_em >= NOW() - INTERVAL '3 minutes') AS usuarios_online,
                    (SELECT COUNT(DISTINCT user_id) FROM mensagens WHERE criado_em >= NOW() - INTERVAL '15 minutes') AS usuarios_recentes;
            """)
            row = cur.fetchone() or {}

    return {
        "total_usuarios": row.get("total_usuarios", 0),
        "total_mensagens": row.get("total_mensagens", 0),
        "total_memorias": row.get("total_memorias", 0),
        "mensagens_hoje": row.get("mensagens_hoje", 0),
        "usuarios_hoje": row.get("usuarios_hoje", 0),
        "usuarios_online": row.get("usuarios_online", 0),
        "usuarios_recentes": row.get("usuarios_recentes", 0),
    }


def listar_usuarios_admin(limite=100):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH ultima AS (
                    SELECT DISTINCT ON (user_id)
                        user_id,
                        role AS ultima_role,
                        content AS ultima_mensagem,
                        criado_em AS ultima_interacao
                    FROM mensagens
                    ORDER BY user_id, criado_em DESC, id DESC
                ), totais AS (
                    SELECT user_id, COUNT(*) AS total_mensagens
                    FROM mensagens
                    GROUP BY user_id
                )
                SELECT
                    u.user_id,
                    u.nome,
                    u.idade,
                    u.cidade,
                    u.criado_em,
                    u.atualizado_em,
                    COALESCE(t.total_mensagens, 0) AS total_mensagens,
                    ul.ultima_role,
                    ul.ultima_mensagem,
                    ul.ultima_interacao,
                    CASE
                        WHEN ul.ultima_interacao IS NULL THEN NULL
                        ELSE EXTRACT(EPOCH FROM (NOW() - ul.ultima_interacao)) / 60
                    END AS minutos_desde_ultima
                FROM usuarios u
                LEFT JOIN ultima ul ON ul.user_id = u.user_id
                LEFT JOIN totais t ON t.user_id = u.user_id
                ORDER BY COALESCE(ul.ultima_interacao, u.atualizado_em, u.criado_em) DESC
                LIMIT %s;
            """, (limite,))
            rows = cur.fetchall()

    usuarios = []
    for row in rows:
        minutos = row.get("minutos_desde_ultima")
        minutos_float = float(minutos) if minutos is not None else None
        usuarios.append({
            "user_id": row.get("user_id"),
            "nome": row.get("nome") or "sem nome",
            "idade": row.get("idade"),
            "cidade": row.get("cidade"),
            "criado_em": row.get("criado_em").isoformat() if row.get("criado_em") else None,
            "atualizado_em": row.get("atualizado_em").isoformat() if row.get("atualizado_em") else None,
            "total_mensagens": row.get("total_mensagens", 0),
            "ultima_role": row.get("ultima_role"),
            "ultima_mensagem": row.get("ultima_mensagem") or "",
            "ultima_interacao": row.get("ultima_interacao").isoformat() if row.get("ultima_interacao") else None,
            "minutos_desde_ultima": minutos_float,
            "status": _status_por_minutos(minutos_float),
        })

    return usuarios


def buscar_conversa_admin(user_id, limite=300):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, role, content, criado_em
                FROM mensagens
                WHERE user_id = %s
                ORDER BY id ASC
                LIMIT %s;
            """, (user_id, limite))
            rows = cur.fetchall()

    return [{
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "role": row.get("role"),
        "content": row.get("content"),
        "criado_em": row.get("criado_em").isoformat() if row.get("criado_em") else None,
    } for row in rows]


def buscar_memorias_admin(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chave, valor, atualizado_em
                FROM memorias
                WHERE user_id = %s
                ORDER BY atualizado_em DESC;
            """, (user_id,))
            rows = cur.fetchall()

    return [{
        "chave": row.get("chave"),
        "valor": row.get("valor"),
        "atualizado_em": row.get("atualizado_em").isoformat() if row.get("atualizado_em") else None,
    } for row in rows]


def buscar_usuario_admin(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, nome, idade, cidade, criado_em, atualizado_em
                FROM usuarios
                WHERE user_id = %s;
            """, (user_id,))
            row = cur.fetchone()

    if not row:
        return None

    return {
        "user_id": row.get("user_id"),
        "nome": row.get("nome") or "sem nome",
        "idade": row.get("idade"),
        "cidade": row.get("cidade"),
        "criado_em": row.get("criado_em").isoformat() if row.get("criado_em") else None,
        "atualizado_em": row.get("atualizado_em").isoformat() if row.get("atualizado_em") else None,
    }


def buscar_dashboard_admin():
    return {
        "metricas": buscar_metricas_admin(),
        "usuarios": listar_usuarios_admin(limite=100),
    }
