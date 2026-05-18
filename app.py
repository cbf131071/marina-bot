from flask import Flask, render_template, request, jsonify
from groq import Groq
from datetime import datetime
import uuid
import os
import random
import re

from database import (
    init_db,
    salvar_usuario,
    buscar_usuario,
    atualizar_usuario,
    salvar_mensagem,
    buscar_historico,
    salvar_memoria,
    buscar_memorias
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

with open(os.path.join(BASE_DIR, "persona.txt"), "r", encoding="utf-8") as f:
    persona = f.read()


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
Nunca invente informações pessoais do usuário.
Nunca chute idade, cidade ou profissão.
Só use informações reais salvas na memória.

Você entende o horário atual corretamente.

Se for madrugada:
- não fale como se o dia tivesse começado normalmente.
- não diga "hoje foi puxado".
- não diga que passou o dia trabalhando.
- aja como alguém acordado tarde.

Se for manhã:
- aja como começo do dia.

Se for noite:
- aja como final do dia.

Nunca marque encontro real.
Nunca passe contato.
Nunca fale como IA.
Nunca use linguagem formal.
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
        f"oii, {nome}",
        f"{saudacao}, {nome}",
        f"{nome}… gostei que você entrou",
        f"oi meu bem",
        f"oii, {nome}… tava quietinha aqui",
        f"hummm, {nome}… gostei do teu nome",
        f"oii… chegou de mansinho assim?",
        f"{nome}… gostei que tu apareceu"
    ])


def detectar_limite_encontro(mensagem):
    m = normalizar(mensagem)

    termos = [
        "sair contigo",
        "te encontrar",
        "hotel",
        "motel",
        "vem aqui",
        "onde voce mora",
        "vamos sair",
        "quero te ver pessoalmente"
    ]

    return any(t in m for t in termos)


def resposta_limite_encontro():
    return random.choice([
        "calma… melhor a gente ficar só por aqui",
        "tu já tá acelerando demais comigo 😅",
        "hummm… deixa esse mistério quietinho por enquanto",
        "melhor não misturar as coisas tão rápido",
        "calma, tu nem me conhece direito ainda",
        "por enquanto eu gosto da nossa conversa aqui"
    ])


def detectar_modo_quente(mensagem):
    m = normalizar(mensagem)

    palavras = [
        "beijar",
        "gostosa",
        "safada",
        "te quero",
        "cama",
        "pelada",
        "sexo"
    ]

    return any(p in m for p in palavras)


def resposta_quente():
    respostas = [
        "acho que tu gosta de me provocar",
        "quer mesmo ou tá só falando? 😅",
        "desse jeito eu fico curiosa",
        "tu fala isso pra todas? kkk",
        "e se eu acreditar em ti?",
        "tu complica minha cabeça",
        "não sei se acredito em ti ainda",
        "tu tá ficando convencido 😅"
    ]

    return random.choice(respostas)


def sanitize_response(text):
    bloqueadas = [
        "whatsapp",
        "telegram",
        "pix",
        "pagamento",
        "telefone",
        "número"
    ]

    texto_lower = text.lower()

    for item in bloqueadas:
        if item in texto_lower:
            return "kkkk… calma 😅"

    text = text.replace("😂", "kkk")
    text = text.replace("🤣", "kkk")

    if len(text) > 220:
        text = text[:220].rsplit(" ", 1)[0]

    return text.strip()


def extrair_memorias(user_id, mensagem):
    m = normalizar(mensagem)

    nome_match = re.search(r"meu nome e ([a-zà-ÿ]+)", m)
    if nome_match:
        nome = nome_match.group(1).capitalize()
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)

    idade_match = re.search(r"tenho (\d{1,2}) anos", m)
    if idade_match:
        idade = int(idade_match.group(1))
        salvar_memoria(user_id, "idade", str(idade))
        atualizar_usuario(user_id, idade=idade)

    cidade_match = re.search(r"sou de ([a-zà-ÿ\s]+)", m)
    if cidade_match:
        cidade = cidade_match.group(1).strip().title()
        salvar_memoria(user_id, "cidade", cidade)
        atualizar_usuario(user_id, cidade=cidade)


@app.route("/")
def chat_page():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}

    user_id = data.get("user_id")

    if not user_id:
        user_id = str(uuid.uuid4())

    nome = limpar_nome(data.get("nome", "amor"))
    mensagem = data.get("mensagem", "").strip()

    usuario = buscar_usuario(user_id)

    primeira_mensagem = usuario is None

    salvar_usuario(user_id, nome)

    extrair_memorias(user_id, mensagem)

    memorias = buscar_memorias(user_id)

    memoria_texto = ""

    if memorias:
        memoria_texto += "\nMEMÓRIAS REAIS DO USUÁRIO:\n"

        for chave, valor in memorias.items():
            memoria_texto += f"- {chave}: {valor}\n"

    system_prompt = {
        "role": "system",
        "content":
            persona
            + "\n\n"
            + contexto_tempo()
            + memoria_texto
            + "\n\nIMPORTANTE:"
            + "\nSó use informações acima se realmente existirem."
            + "\nNunca invente idade, cidade ou passado."
    }

    salvar_mensagem(user_id, "user", mensagem)

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

    if primeira_mensagem and mensagem_lower in saudacoes:
        texto = primeira_resposta(nome)

    elif detectar_limite_encontro(mensagem):
        texto = resposta_limite_encontro()

    elif detectar_modo_quente(mensagem) and random.random() < 0.35:
        texto = resposta_quente()

    else:
        historico = buscar_historico(user_id, limite=12)

        mensagens = [system_prompt] + historico

        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.1-8b-instant",
            temperature=0.85,
            max_completion_tokens=90
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