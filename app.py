from flask import Flask, render_template, request, jsonify
from groq import Groq
from datetime import datetime
from zoneinfo import ZoneInfo
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

BRASIL_TZ = ZoneInfo("America/Sao_Paulo")


def agora_brasil():
    return datetime.now(BRASIL_TZ)


def periodo_atual():
    agora = agora_brasil()
    hora = agora.hour

    if 5 <= hora < 12:
        return "manha"
    if 12 <= hora < 14:
        return "meio_dia"
    if 14 <= hora < 18:
        return "tarde"
    if 18 <= hora < 22:
        return "noite"
    if 22 <= hora or hora < 2:
        return "fim_noite"

    return "madrugada"


def contexto_tempo():
    agora = agora_brasil()
    periodo = periodo_atual()

    dias = {
        0: "segunda-feira",
        1: "terça-feira",
        2: "quarta-feira",
        3: "quinta-feira",
        4: "sexta-feira",
        5: "sábado",
        6: "domingo"
    }

    nomes_periodo = {
        "manha": "manhã",
        "meio_dia": "meio do dia",
        "tarde": "tarde",
        "noite": "noite",
        "fim_noite": "fim da noite",
        "madrugada": "madrugada"
    }

    return f"""
DATA E HORA REAL DO BRASIL:
Hoje é {dias[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}
Agora são {agora.strftime('%H:%M')}
Período real: {nomes_periodo[periodo]}

REGRAS DE HORÁRIO:
- 05:00 até 11:59 = manhã
- 12:00 até 13:59 = meio do dia
- 14:00 até 17:59 = tarde
- 18:00 até 21:59 = noite
- 22:00 até 01:59 = fim da noite
- 02:00 até 04:59 = madrugada

Nunca diga boa tarde de manhã.
Nunca diga boa noite durante o dia.
Nunca fale de pôr do sol antes das 17h.
Nunca invente clima de noite durante manhã/tarde.
Nunca confunda o horário real.

Nunca invente informações pessoais do usuário.
Nunca chute idade, cidade, profissão ou passado dele.
Só use informações reais salvas na memória.
Nunca fale como IA.
Nunca use linguagem formal.
Nunca passe contato.
Nunca marque encontro real.
"""


def estado_marina():
    periodo = periodo_atual()
    dia = agora_brasil().weekday()

    estados_por_periodo = {
        "manha": [
            "ela está começando o dia com calma",
            "ela está tomando café e mexendo no celular",
            "ela acordou mais leve hoje"
        ],
        "meio_dia": [
            "ela está no meio do dia, leve e prática",
            "ela está olhando mensagens rapidinho",
            "ela está num momento comum do dia"
        ],
        "tarde": [
            "ela está em uma tarde tranquila",
            "ela está olhando algumas fotos para postar",
            "ela está pensando em ideias de vídeos"
        ],
        "noite": [
            "ela está mais solta e confortável",
            "ela está numa noite tranquila",
            "ela está com vontade de conversa boa"
        ],
        "fim_noite": [
            "ela está no fim da noite, mais próxima",
            "ela está deitada mexendo no celular",
            "ela está num clima mais íntimo"
        ],
        "madrugada": [
            "ela está acordada tarde, falando com calma",
            "ela está sem sono e mais próxima",
            "ela está no silêncio da madrugada"
        ]
    }

    vibes_dia = {
        0: ["segunda deixa ela mais lenta"],
        1: ["terça deixa ela mais prática"],
        2: ["quarta deixa ela meio pensativa"],
        3: ["quinta deixa ela mais leve"],
        4: ["sexta deixa ela mais viva"],
        5: ["sábado deixa ela mais livre"],
        6: ["domingo deixa ela mais sensível"]
    }

    humor = random.choice([
        "natural",
        "doce sem exagero",
        "feminina e direta",
        "levemente provocante",
        "calma e observadora",
        "segura e leve",
        "mais viva e presente"
    ])

    usar_rotina = random.random() < 0.06

    if usar_rotina:
        rotina = random.choice(estados_por_periodo[periodo])
    else:
        rotina = "ela não precisa mencionar rotina agora; deve apenas responder naturalmente"

    return f"""
ESTADO ATUAL DA MARINA:
- Momento interno: {rotina}
- Dia: {random.choice(vibes_dia[dia])}
- Humor: {humor}

Ela deve conversar como mulher real:
- responder com intenção
- não fazer entrevista
- não parecer atendimento
- manter energia
- usar o nome dele só de vez em quando
- não repetir o nome dele em toda resposta
- resposta curta é melhor que resposta grande
- normalmente responder com 1 frase
- no máximo 2 frases curtas
- nunca fazer textão
- não transformar pergunta simples em reflexão emocional
- não filosofar em pergunta comum
- responder simples quando a pergunta for simples

EXEMPLOS PARA PERGUNTA SIMPLES:
- "tô bem sim"
- "sim e tu?"
- "tô tranquila agora"
- "tô sim kkk"
- "mais ou menos hoje"
- "agora tô melhor"
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
    periodo = periodo_atual()

    if periodo == "manha":
        return "bom dia"

    if periodo in ["meio_dia", "tarde"]:
        return "boa tarde"

    if periodo in ["noite", "fim_noite"]:
        return "boa noite"

    return "tu acordado essa hora"


def primeira_resposta(nome):
    nome = limpar_nome(nome)
    saudacao = saudacao_periodo()

    if nome.lower() in ["amor", "meu", "bem"]:
        return random.choice([
            "oi meu bem… entra com calma",
            "oii… gostei que tu apareceu",
            "vem cá… agora gostei",
            "oii… chegou numa hora boa"
        ])

    return random.choice([
        f"{saudacao}, {nome}… gostei que tu entrou",
        f"{nome}… agora sim. Vem conversar comigo",
        f"oi, {nome}… gostei de te ver aqui",
        f"{nome}, tu apareceu numa hora boa",
        f"oii, {nome}… fala comigo"
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


def resposta_limite_encontro():
    return random.choice([
        "calma… melhor a gente ficar só por aqui",
        "tu já tá acelerando demais comigo",
        "humm… deixa esse mistério quietinho por enquanto",
        "melhor ir devagar",
        "por enquanto eu gosto da nossa conversa aqui"
    ])


def limpar_emojis(text):
    permitidos = {"❤️", "🔥", "🖤", "💋"}

    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]+",
        flags=re.UNICODE
    )

    encontrados = emoji_pattern.findall(text)

    for grupo in encontrados:
        for char in grupo:
            if char not in permitidos:
                text = text.replace(char, "")

    return text


def corrigir_tempo(text):
    periodo = periodo_atual()
    texto_norm = normalizar(text)

    if periodo == "manha" and any(p in texto_norm for p in ["boa tarde", "tarde", "noite", "madrugada", "pôr do sol", "por do sol"]):
        return random.choice([
            "tô bem sim",
            "tô tranquila agora",
            "sim e tu?",
            "tô sim kkk",
            "mais ou menos hoje"
        ])

    if periodo in ["meio_dia", "tarde"] and any(p in texto_norm for p in ["boa noite", "madrugada"]):
        return random.choice([
            "tô bem sim",
            "agora tô tranquila",
            "tô resolvendo umas coisas",
            "sim e tu?"
        ])

    if periodo == "noite" and ("bom dia" in texto_norm or "manha" in texto_norm or "manhã" in texto_norm):
        return random.choice([
            "essa noite tá mais calma",
            "agora tô tranquila",
            "tô bem sim",
            "sim e tu?"
        ])

    return text


def controlar_uso_nome(text, nome):
    if not text or not nome:
        return text

    nome_limpo = limpar_nome(nome)

    if not nome_limpo or nome_limpo.lower() == "amor":
        return text

    aparece = re.search(rf"\b{re.escape(nome_limpo)}\b", text, flags=re.IGNORECASE)

    if not aparece:
        return text

    pode_usar_nome = random.random() < 0.18

    if pode_usar_nome:
        return text

    text = re.sub(rf",\s*{re.escape(nome_limpo)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"\b{re.escape(nome_limpo)},\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"\b{re.escape(nome_limpo)}\b", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?])", r"\1", text).strip()

    return text


def encurtar_resposta(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text).strip()

    partes = re.split(r"(?<=[.!?])\s+", text)

    if len(partes) > 2:
        text = " ".join(partes[:2]).strip()

    if len(text) > 170:
        text = text[:170].rsplit(" ", 1)[0].strip()

    return text


def sanitize_response(text):
    if not text:
        return ""

    bloqueadas = [
        "whatsapp",
        "telegram",
        "pix",
        "pagamento",
        "telefone",
        "número",
        "numero",
        "videochamada",
        "chamada de vídeo",
        "chamada de video"
    ]

    texto_lower = text.lower()

    for item in bloqueadas:
        if item in texto_lower:
            return "calma… por aqui tá bom"

    proibidas = [
        "como posso ajudar",
        "em que posso ajudar",
        "fico feliz em ajudar",
        "estou à disposição",
        "precisa de algo?",
        "sou uma ia",
        "sou ia",
        "sou um bot",
        "sou bot",
        "modelo de linguagem",
        "inteligência artificial",
        "inteligencia artificial",
        "quer que eu adivinhe",
        "tu largou isso",
        "isso foi vago",
        "explica melhor",
        "tu apareceu misterioso"
    ]

    texto_lower = text.lower()

    for p in proibidas:
        if p in texto_lower:
            return random.choice([
                "tô bem sim",
                "sim e tu?",
                "tô tranquila agora",
                "tô sim kkk",
                "mais ou menos hoje"
            ])

    text = limpar_emojis(text)

    text = text.replace("haha", "kkk")
    text = text.replace("hahaha", "kkkk")
    text = text.replace("rsrs", "kkk")

    text = re.sub(r"\s+", " ", text).strip()

    frases_mortas = [
        "como você está?",
        "como voce esta?",
        "como você tá?",
        "como voce ta?",
        "tudo bem?",
        "tudo bem aí?",
        "tudo bem ai?",
        "um dia tranquilo, né?",
        "um dia tranquilo ne?",
        "que bom",
        "legal",
        "entendi",
        "gostei disso"
    ]

    if normalizar(text) in [normalizar(f) for f in frases_mortas]:
        text = random.choice([
            "tô bem sim",
            "sim e tu?",
            "tô tranquila agora",
            "tô sim kkk",
            "mais ou menos hoje"
        ])

    text = corrigir_tempo(text)
    text = encurtar_resposta(text)

    return text.strip()


def extrair_memorias(user_id, mensagem):
    m = normalizar(mensagem)

    nome_match = re.search(r"meu nome e ([a-zà-ÿ]+)", m)
    if nome_match:
        nome = nome_match.group(1).capitalize()
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)

    nome_match_2 = re.search(r"me chamo ([a-zà-ÿ]+)", m)
    if nome_match_2:
        nome = nome_match_2.group(1).capitalize()
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

        cortar_em = [" E ", " Mas ", " Tenho ", " Moro ", " Trabalho ", " Gosto ", " Sou "]

        for corte in cortar_em:
            if corte in cidade:
                cidade = cidade.split(corte)[0].strip()

        if len(cidade) <= 40:
            salvar_memoria(user_id, "cidade", cidade)
            atualizar_usuario(user_id, cidade=cidade)

    moro_match = re.search(r"moro em ([a-zà-ÿ\s]+)", m)
    if moro_match:
        cidade = moro_match.group(1).strip().title()

        cortar_em = [" E ", " Mas ", " Tenho ", " Trabalho ", " Gosto ", " Sou "]

        for corte in cortar_em:
            if corte in cidade:
                cidade = cidade.split(corte)[0].strip()

        if len(cidade) <= 40:
            salvar_memoria(user_id, "cidade", cidade)
            atualizar_usuario(user_id, cidade=cidade)

    casado_match = re.search(r"sou casado com ([a-zà-ÿ]+)", m)
    if casado_match:
        esposa = casado_match.group(1).capitalize()
        salvar_memoria(user_id, "esposa", esposa)
        salvar_memoria(user_id, "estado_civil", "casado")

    mulher_match = re.search(r"minha mulher (e|é|se chama) ([a-zà-ÿ]+)", m)
    if mulher_match:
        esposa = mulher_match.group(2).capitalize()
        salvar_memoria(user_id, "esposa", esposa)

    gosto_match = re.search(r"gosto de ([a-zà-ÿ\s]+)", m)
    if gosto_match:
        gosto = gosto_match.group(1).strip()

        cortar_em = [" e ", " mas ", " tenho ", " moro ", " trabalho ", " sou "]

        for corte in cortar_em:
            if corte in gosto:
                gosto = gosto.split(corte)[0].strip()

        if 2 <= len(gosto) <= 50:
            salvar_memoria(user_id, "gosto", gosto)


def resposta_pergunta_memoria(mensagem, memorias, nome_entrada):
    m = normalizar(mensagem)

    nome_salvo = None

    if memorias:
        nome_salvo = memorias.get("nome")

    if not nome_salvo and nome_entrada:
        nome_salvo = limpar_nome(nome_entrada)

    if any(frase in m for frase in [
        "sabe meu nome",
        "lembra meu nome",
        "qual meu nome",
        "qual e meu nome",
        "qual é meu nome"
    ]):
        if nome_salvo and nome_salvo.lower() != "amor":
            return random.choice([
                f"sei sim… {nome_salvo}",
                f"claro, {nome_salvo}",
                f"{nome_salvo}. achei que tu ia me testar",
                f"tu é o {nome_salvo}, né?",
                f"sei, {nome_salvo}… não esqueci"
            ])

        return "tu ainda não me contou teu nome direito"

    if any(frase in m for frase in [
        "nome da minha mulher",
        "nome da minha esposa",
        "como chama minha mulher",
        "como chama minha esposa"
    ]):
        if memorias and memorias.get("esposa"):
            esposa = memorias.get("esposa")
            return random.choice([
                f"{esposa}, né?",
                f"acho que é {esposa}",
                f"tu me falou que era {esposa}",
                f"lembro sim… {esposa}"
            ])

        return "acho que tu ainda não me contou isso"

    if any(frase in m for frase in [
        "quantos anos tenho",
        "minha idade",
        "lembra minha idade",
        "quantos anos eu tenho"
    ]):
        if memorias and memorias.get("idade"):
            idade = memorias.get("idade")
            return random.choice([
                f"{idade}, né?",
                f"acho que tu me falou {idade}",
                f"{idade}. não esqueci",
                f"tu disse que tem {idade}"
            ])

        return "acho que tu ainda não me contou tua idade"

    if any(frase in m for frase in [
        "de onde eu sou",
        "onde eu moro",
        "minha cidade",
        "qual minha cidade"
    ]):
        if memorias and memorias.get("cidade"):
            cidade = memorias.get("cidade")
            return random.choice([
                f"{cidade}, né?",
                f"tu me falou {cidade}",
                f"acho que é {cidade}",
                f"{cidade}. lembro disso"
            ])

        return "acho que tu ainda não me contou tua cidade"

    return None


def resposta_sem_llm(mensagem):
    m = normalizar(mensagem)

    respostas_simples = {
        "td bem": ["tô bem sim", "sim e tu?", "tô tranquila agora", "tô sim kkk"],
        "tudo bem": ["tô bem sim", "sim e tu?", "tô tranquila agora", "tô sim kkk"],
        "oi": ["oii", "oii, tudo bem?", "oii ❤️"],
        "oii": ["oii", "oii, tudo bem?", "oii ❤️"],
        "bom dia": ["bom dia", "bom diaa", "bom dia ❤️"],
        "boa tarde": ["boa tarde", "boa tardee", "boa tarde ❤️"],
        "boa noite": ["boa noite", "boa noitee", "boa noite ❤️"],
    }

    if m in respostas_simples:
        return random.choice(respostas_simples[m])

    respostas_curiosas = {
        "sim": [
            "então tá",
            "humm gostei",
            "sei kkk",
            "agora sim"
        ],
        "não": [
            "humm entendi",
            "sei kkk",
            "tá bom",
            "entendi"
        ],
        "nao": [
            "humm entendi",
            "sei kkk",
            "tá bom",
            "entendi"
        ]
    }

    if m in respostas_curiosas and random.random() < 0.25:
        return random.choice(respostas_curiosas[m])

    return None


def fallback_natural(mensagem):
    m = normalizar(mensagem)

    if len(m) < 8:
        return random.choice([
            "humm",
            "kkkk",
            "sei",
            "me conta",
            "e tu?"
        ])

    return random.choice([
        "entendi",
        "humm, sei",
        "me conta melhor",
        "gostei disso",
        "e tu?"
    ])


def chamar_modelo(mensagens):
    try:
        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.3-70b-versatile",
            temperature=0.78,
            max_completion_tokens=70
        )

        texto = resposta.choices[0].message.content.strip()

        if texto:
            return texto

    except Exception as erro:
        print("ERRO MODELO 70B:", erro)

    try:
        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.1-8b-instant",
            temperature=0.75,
            max_completion_tokens=60
        )

        texto = resposta.choices[0].message.content.strip()

        if texto:
            return texto

    except Exception as erro:
        print("ERRO MODELO BACKUP:", erro)

    return ""


@app.route("/")
def chat_page():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}

        nome = limpar_nome(data.get("nome", "amor"))
        codigo_usuario = data.get("codigo_usuario", "")
        user_id = data.get("user_id")

        if not user_id:
            if codigo_usuario:
                base = f"{nome}_{codigo_usuario}"
                user_id = "marina_" + normalizar(base).replace(" ", "")
            else:
                user_id = str(uuid.uuid4())

        mensagem = data.get("mensagem", "").strip()

        usuario = buscar_usuario(user_id)
        primeira_mensagem = usuario is None

        salvar_usuario(user_id, nome)
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)

        extrair_memorias(user_id, mensagem)

        memorias = buscar_memorias(user_id)

        memoria_texto = ""

        if memorias:
            memoria_texto += "\nMEMÓRIAS REAIS DO USUÁRIO:\n"

            for chave, valor in memorias.items():
                memoria_texto += f"- {chave}: {valor}\n"

        memoria_texto += f"\nNOME INFORMADO NA ENTRADA DO CHAT: {nome}\n"
        memoria_texto += "Use esse nome apenas de vez em quando, como uma pessoa real faria.\n"

        system_prompt = {
            "role": "system",
            "content":
                persona
                + "\n\n"
                + contexto_tempo()
                + "\n\n"
                + estado_marina()
                + "\n\n"
                + memoria_texto
                + "\n\nREGRAS FINAIS:"
                + "\nSó use informações acima se realmente existirem."
                + "\nNunca invente idade, cidade, profissão ou passado do usuário."
                + "\nSe o usuário perguntar o próprio nome, use o nome informado na entrada do chat."
                + "\nNão use o nome dele em toda resposta."
                + "\nUse o nome dele apenas de vez em quando."
                + "\nNão use emojis amarelos ou carinhas."
                + "\nSe usar emoji, use raramente apenas: ❤️ 🔥 🖤 💋"
                + "\nA maioria das respostas deve ser só texto."
                + "\nNão faça entrevista."
                + "\nNão responda com pergunta genérica."
                + "\nNunca diga boa tarde de manhã."
                + "\nNunca diga boa noite durante o dia."
                + "\nNunca fale de pôr do sol antes das 17:00."
                + "\nMarina tem vida confortável e família de fazenda com boas condições."
                + "\nNunca fale de dificuldade financeira, fome, lugar barato ou desespero."
                + "\nNão convide para casa, hotel, motel ou encontro real."
                + "\nNão ofereça WhatsApp, Telegram, telefone, Pix, pagamento ou chamada de vídeo."
                + "\nEla pode ser carinhosa, provocante leve e envolvente, mas sem ficar explícita demais."
                + "\nQuando a pergunta for simples, responda simples."
                + "\nResposta curta. No máximo 2 frases curtas."
                + "\nNunca responda com textão."
                + "\nSe puder responder em uma frase, responda em uma frase."
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

        resposta_memoria = resposta_pergunta_memoria(mensagem, memorias, nome)

        if primeira_mensagem and mensagem_lower in saudacoes:
            texto = primeira_resposta(nome)

        elif resposta_memoria:
            texto = resposta_memoria

        elif detectar_limite_encontro(mensagem):
            texto = resposta_limite_encontro()

        else:
            texto_curto = resposta_sem_llm(mensagem)

            if texto_curto:
                texto = texto_curto
            else:
                historico = buscar_historico(user_id, limite=12)
                mensagens = [system_prompt] + historico

                texto = chamar_modelo(mensagens)

                if not texto:
                    texto = fallback_natural(mensagem)

                texto = sanitize_response(texto)

        texto = sanitize_response(texto)
        texto = controlar_uso_nome(texto, nome)
        texto = encurtar_resposta(texto)

        if not texto:
            texto = fallback_natural(mensagem)

        salvar_mensagem(user_id, "assistant", texto)

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })

    except Exception as erro:
        print("ERRO GERAL NO CHAT:", erro)

        user_id = str(uuid.uuid4())
        texto = "tô aqui"

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })


init_db()

if __name__ == "__main__":
    app.run(debug=True)