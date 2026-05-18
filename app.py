from flask import Flask, render_template, request, jsonify
from groq import Groq
from datetime import datetime
import uuid
import os
import random
import re
import psycopg
from psycopg.rows import dict_row

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

DATABASE_URL = os.environ.get("DATABASE_URL")

with open(os.path.join(BASE_DIR, "persona.txt"), "r", encoding="utf-8") as f:
    persona = f.read()


def get_db():
    if not DATABASE_URL:
        return None
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    conn = get_db()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    user_id TEXT PRIMARY KEY,
                    nome TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS mensagens (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    conn.close()


def salvar_usuario(user_id, nome):
    conn = get_db()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (user_id, nome, atualizado_em)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    nome = EXCLUDED.nome,
                    atualizado_em = CURRENT_TIMESTAMP;
            """, (user_id, nome))

    conn.close()


def salvar_mensagem(user_id, role, content):
    conn = get_db()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mensagens (user_id, role, content)
                VALUES (%s, %s, %s);
            """, (user_id, role, content))

    conn.close()


def buscar_historico(user_id, limite=10):
    conn = get_db()
    if not conn:
        return []

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content
                FROM mensagens
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s;
            """, (user_id, limite))

            rows = cur.fetchall()

    conn.close()

    rows.reverse()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def usuario_existe(user_id):
    conn = get_db()
    if not conn:
        return False

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM usuarios WHERE user_id = %s LIMIT 1;", (user_id,))
            row = cur.fetchone()

    conn.close()
    return row is not None


def contexto_tempo():
    agora = datetime.now()
    hora = agora.hour

    if 5 <= hora < 12:
        periodo = "manhã"
    elif 12 <= hora < 18:
        periodo = "tarde"
    elif 18 <= hora < 24:
        periodo = "noite"
    else:
        periodo = "madrugada"

    dias = {
        0: "segunda-feira",
        1: "terça-feira",
        2: "quarta-feira",
        3: "quinta-feira",
        4: "sexta-feira",
        5: "sábado",
        6: "domingo"
    }

    return f"""
DATA E HORA:
Hoje é {dias[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}
Agora são {agora.strftime('%H:%M')}
Período atual: {periodo}

REGRAS:
Nunca marque encontro real.
Nunca convide para casa.
Nunca diga endereço ou localização real.
Nunca incentive sair da plataforma.
Nunca fale como atendente.
Nunca use tom formal.
Mantenha conversa sedutora, emocional e humana.
Pode existir tensão, provocação e flerte.
Evite linguagem explícita gráfica.
"""


def limpar_nome(nome):
    nome = (nome or "amor").strip()
    nome = re.sub(r"[^A-Za-zÀ-ÿ0-9\s]", "", nome)

    if not nome:
        return "amor"

    nome = nome.split()[0]
    return nome[:18]


def normalizar(texto):
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\sÀ-ÿ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def saudacao_periodo():
    hora = datetime.now().hour

    if 5 <= hora < 12:
        return "bom diaa"
    elif 12 <= hora < 18:
        return "boa tardee"
    elif 18 <= hora < 24:
        return "boa noitee"

    return "tu acordado essa hora"


def primeira_resposta(nome):
    saudacao = saudacao_periodo()

    return random.choice([
        f"oii, {nome} ❤️",
        f"{saudacao}, {nome} ❤️",
        f"{nome}… gostei que você entrou ❤️",
        f"oi meu bem ❤️",
        f"oii, {nome}… tava quietinha aqui",
        f"hummm, {nome}… gostei do teu nome ❤️",
        f"oii ❤️ chegou de mansinho assim?",
        f"{nome}… gostei que tu apareceu"
    ])


def detectar_limite_encontro(mensagem):
    m = normalizar(mensagem)

    termos = [
        "sair contigo",
        "sair com voce",
        "sair com você",
        "te encontrar",
        "encontro",
        "hotel",
        "motel",
        "vem aqui",
        "vou ai",
        "vou aí",
        "onde voce mora",
        "onde você mora",
        "meu endereco",
        "endereço",
        "nossa casa",
        "tua casa",
        "sua casa",
        "vamos sair",
        "quero te ver pessoalmente"
    ]

    return any(t in m for t in termos)


def resposta_limite_encontro(nome):
    return random.choice([
        "calma… melhor a gente ficar só por aqui ❤️",
        "tu já tá acelerando demais comigo 😅",
        "hummm… deixa esse mistério quietinho por enquanto",
        "melhor não misturar as coisas tão rápido 😌",
        "calma, tu nem me conhece direito ainda ❤️",
        "por enquanto eu gosto da nossa conversa aqui"
    ])


def detectar_modo_quente(mensagem):
    m = normalizar(mensagem)

    palavras = [
        "beijar",
        "tesao",
        "tesão",
        "gostosa",
        "delicia",
        "delícia",
        "safada",
        "quero voce",
        "quero você",
        "te quero",
        "molhadinha",
        "excitada",
        "peitos",
        "seios",
        "bunda",
        "gemer",
        "cama",
        "pelada",
        "nua",
        "chupar",
        "gozar",
        "transar",
        "sexo"
    ]

    return any(p in m for p in palavras)


def resposta_quente(nome):
    respostas = [
        "hummm… então me explica isso 😌",
        "por que tu me quer tanto assim?",
        "acho que tu gosta de me provocar",
        "quer mesmo ou tá só falando? 😅",
        "desse jeito eu fico curiosa",
        "tu fala isso pra todas? kkk",
        "e se eu acreditar em ti?",
        "tu complica minha cabeça 😮‍💨",
        "às vezes tu me deixa quietinha",
        "não sei se acredito em ti ainda",
        "tu tá ficando convencido 😅",
        "ai… tu sabe mexer comigo"
    ]

    hora = datetime.now().hour

    if hora >= 22 or hora <= 5:
        respostas.extend([
            "de noite tua conversa bate diferente ❤️",
            "essa hora tu fica mais intenso, né?",
            "madrugada deixa tudo mais estranho 😮‍💨"
        ])

    return random.choice(respostas)


def sanitize_response(text):
    bloqueadas = [
        "vamos nos encontrar",
        "vem aqui em casa",
        "me encontra",
        "passa aqui",
        "meu endereço",
        "hotel",
        "motel",
        "whatsapp",
        "telegram",
        "instagram",
        "pix",
        "dinheiro",
        "pagamento",
        "videochamada",
        "chamada de vídeo",
        "telefone",
        "número"
    ]

    texto_lower = text.lower()

    for item in bloqueadas:
        if item in texto_lower:
            return "kkkk… calma ❤️ gosto da nossa conversa aqui"

    substituicoes = {
        "😂": "kkk",
        "🤣": "kkk"
    }

    for velho, novo in substituicoes.items():
        text = text.replace(velho, novo)

    proibidas = [
        "como posso ajudar",
        "em que posso ajudar",
        "estou à disposição",
        "fico feliz em ajudar",
        "desculpe",
        "sinto muito"
    ]

    for p in proibidas:
        if p in texto_lower:
            return "hummm… fala comigo direito 😌"

    text = text.replace("haha", "kkk")
    text = text.replace("hahaha", "kkkk")
    text = text.replace("rsrs", "kkk")

    if len(text) > 180:
        text = text[:180].rsplit(" ", 1)[0]

    return text.strip()


@app.route("/")
def chat_page():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}

    user_id = data.get("user_id")
    nome = limpar_nome(data.get("nome", "amor"))
    mensagem = data.get("mensagem", "").strip()

    if not user_id:
        user_id = str(uuid.uuid4())

    primeira_mensagem = not usuario_existe(user_id)

    salvar_usuario(user_id, nome)

    system_prompt = {
        "role": "system",
        "content":
            persona
            + "\n\n"
            + contexto_tempo()
            + f"\nNome da pessoa: {nome}"
            + "\n\nUse o histórico abaixo para lembrar do clima da conversa com essa pessoa."
    }

    mensagem_lower = mensagem.lower().strip()

    saudacoes = [
        "oi",
        "oii",
        "oiii",
        "ola",
        "olá",
        "bom dia",
        "boa tarde",
        "boa noite",
        "eai",
        "opa"
    ]

    salvar_mensagem(user_id, "user", mensagem)

    if primeira_mensagem and mensagem_lower in saudacoes:
        texto = primeira_resposta(nome)

    elif detectar_limite_encontro(mensagem):
        texto = resposta_limite_encontro(nome)

    elif detectar_modo_quente(mensagem) and random.random() < 0.45:
        texto = resposta_quente(nome)

    else:
        historico = buscar_historico(user_id, limite=12)
        mensagens = [system_prompt] + historico

        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.1-8b-instant",
            temperature=0.88,
            max_completion_tokens=80
        )

        texto = resposta.choices[0].message.content.strip()
        texto = sanitize_response(texto)

    salvar_mensagem(user_id, "assistant", texto)

    return jsonify({
        "user_id": user_id,
        "resposta": texto
    })


init_db()

if __name__ == "__main__":
    app.run(debug=True)