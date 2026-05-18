from flask import Flask, render_template, request, jsonify
from groq import Groq
from datetime import datetime
import uuid
import os
import random
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

with open(os.path.join(BASE_DIR, "persona.txt"), "r", encoding="utf-8") as f:
    persona = f.read()

historicos = {}

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
        f"tava te esperando aparecer, {nome} 😏",
        f"oi meu bem ❤️",
        f"hummm… então é você 😈",
        f"{nome}… gostei que você entrou ❤️",
        f"já chegou mexendo comigo 😏",
        f"oii ❤️ tava quietinha aqui…"
    ])

def detectar_limite_encontro(mensagem):
    m = normalizar(mensagem)

    termos = [
        "sair contigo",
        "sair com voce",
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
        "calma 😏 tu já tá acelerando demais comigo...",
        "hummm… melhor a gente continuar só nesse clima aqui ❤️",
        "tu é perigoso quando começa assim 😈",
        "vai devagar comigo… eu gosto da tensão 😏",
        "não estraga o mistério tão rápido ❤️",
        "prefiro deixar na imaginação por enquanto 😈"
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
        "tu gosta de mexer comigo 😏",
        "desse jeito eu vou acabar entrando no clima ❤️",
        "hummm… continua falando assim 😈",
        "tu sabe provocar direitinho 😏",
        "ai… tua conversa mexe comigo ❤️",
        "perigoso conversar contigo desse jeito 😈",
        "não me olha assim… 😏",
        "tu tá me deixando imaginando coisa ❤️",
        "desse jeito eu fico sem reação 😈",
        "tu adora me testar né ❤️"
    ]

    hora = datetime.now().hour

    if hora >= 22 or hora <= 5:
        respostas.extend([
            "essa hora tu fica ainda mais perigoso 😈",
            "madrugada contigo é complicado 😏",
            "de noite tua conversa bate diferente ❤️"
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
            return "kkkk… calma ❤️ gosto da nossa conversa aqui 😏"

    substituicoes = {
        "😊": "❤️",
        "☺️": "❤️",
        "😁": "😏",
        "😅": "😏",
        "🤭": "😏",
        "😉": "😏",
        "🙂": "❤️",
        "😄": "❤️",
        "😃": "❤️",
        "😂": "kkk 😈",
        "🤣": "kkk 😈"
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
            return "hummm… fala comigo direito 😏"

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
    data = request.json

    user_id = data.get("user_id")
    nome = limpar_nome(data.get("nome", "amor"))
    mensagem = data.get("mensagem", "").strip()

    if not user_id:
        user_id = str(uuid.uuid4())

    primeira_mensagem = user_id not in historicos

    if user_id not in historicos:
        historicos[user_id] = [{
            "role": "system",
            "content":
                persona
                + "\n\n"
                + contexto_tempo()
                + f"\nNome da pessoa: {nome}"
        }]

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

    historicos[user_id].append({
        "role": "user",
        "content": mensagem
    })

    if primeira_mensagem and mensagem_lower in saudacoes:
        texto = primeira_resposta(nome)

    elif detectar_limite_encontro(mensagem):
        texto = resposta_limite_encontro(nome)

    elif detectar_modo_quente(mensagem) and random.random() < 0.45:
        texto = resposta_quente(nome)

    else:
        mensagens = [historicos[user_id][0]] + historicos[user_id][-8:]

        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.1-8b-instant",
            temperature=0.88,
            max_completion_tokens=80
        )

        texto = resposta.choices[0].message.content.strip()
        texto = sanitize_response(texto)

    historicos[user_id].append({
        "role": "assistant",
        "content": texto
    })

    return jsonify({
        "user_id": user_id,
        "resposta": texto
    })

if __name__ == "__main__":
    app.run(debug=True)