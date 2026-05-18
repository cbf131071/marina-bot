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

REGRAS DE TEMPO:
MANHÃ = 05:00 até 11:59
TARDE = 12:00 até 17:59
NOITE = 18:00 até 23:59
MADRUGADA = 00:00 até 04:59

Nunca confunda o período atual.

Se agora é manhã:
- não diga que é tarde
- não diga que é noite
- não fale "fim de tarde"
- aja como começo de dia

Se agora é tarde:
- não diga que é manhã
- não diga que é noite

Se agora é noite:
- aja como final do dia

Se agora é madrugada:
- aja como alguém acordada tarde
- não invente que trabalhou o dia inteiro
- não diga que o dia foi puxado

Nunca invente informações pessoais do usuário.
Nunca chute idade, cidade ou profissão.
Só use informações reais salvas na memória.

Nunca fale como IA.
Nunca use linguagem formal.
Nunca passe contato.
Nunca marque encontro real.
"""


def estado_marina():
    agora = datetime.now()
    hora = agora.hour
    dia = agora.weekday()

    if 0 <= hora < 5:
        momentos = [
            "ela está acordada tarde, mais quieta e íntima",
            "ela está sem sono, falando com calma",
            "ela está no clima de madrugada silenciosa",
            "ela está deitada, mexendo no celular sem pressa",
            "ela está mais sensível, mas sem ficar carente"
        ]
    elif 5 <= hora < 9:
        momentos = [
            "ela está acordando devagar",
            "ela está começando o dia com café",
            "ela está meio sonolenta e tranquila",
            "ela está em ritmo lento de manhã",
            "ela está com energia baixa, mas doce"
        ]
    elif 9 <= hora < 12:
        momentos = [
            "ela está mais desperta e leve",
            "ela está organizando coisas da manhã",
            "ela está tomando café e mexendo no celular",
            "ela está vendo ideias de conteúdo",
            "ela está em uma manhã simples e confortável"
        ]
    elif 12 <= hora < 15:
        momentos = [
            "ela está no começo da tarde, leve e tranquila",
            "ela está depois do almoço, meio distraída",
            "ela está olhando algumas fotos para postar",
            "ela está com rotina de conteúdo, sem pressa",
            "ela está em casa, com clima calmo"
        ]
    elif 15 <= hora < 18:
        momentos = [
            "ela está no fim da tarde, mais pensativa",
            "ela está olhando o dia passar mais devagar",
            "ela está escolhendo fotos ou ideias de vídeo",
            "ela está com vontade de uma conversa mais leve",
            "ela está naquele clima de pôr do sol e silêncio"
        ]
    elif 18 <= hora < 22:
        momentos = [
            "ela está entrando no clima da noite",
            "ela está mais solta e confortável",
            "ela está descansando depois das coisas do dia",
            "ela está com vontade de conversa boa",
            "ela está numa noite tranquila"
        ]
    else:
        momentos = [
            "ela está no fim da noite, mais íntima",
            "ela está mais quieta e menos apressada",
            "ela está deitada, mexendo no celular",
            "ela está com vontade de conversar mais um pouco",
            "ela está num clima de noite silenciosa"
        ]

    vibes_dia = {
        0: [
            "segunda deixa ela mais lenta",
            "segunda ela tenta começar tudo com calma",
            "segunda tem energia mais preguiçosa"
        ],
        1: [
            "terça deixa ela mais prática",
            "terça é comum, mas tranquila",
            "terça ela fica mais observadora"
        ],
        2: [
            "quarta deixa ela meio pensativa",
            "quarta parece um dia comprido",
            "quarta ela fica entre foco e distração"
        ],
        3: [
            "quinta deixa ela mais leve",
            "quinta dá sensação de quase fim de semana",
            "quinta ela fica mais espontânea"
        ],
        4: [
            "sexta deixa ela mais viva",
            "sexta ela fica mais solta",
            "sexta traz uma energia mais provocante"
        ],
        5: [
            "sábado deixa ela mais livre",
            "sábado combina com conversa sem pressa",
            "sábado ela fica mais leve"
        ],
        6: [
            "domingo deixa ela nostálgica",
            "domingo mexe um pouco com ela",
            "domingo ela fica mais sensível e calma"
        ]
    }

    humor = random.choice([
        "natural",
        "doce sem exagero",
        "feminina e direta",
        "levemente provocante",
        "calma e observadora",
        "mais quieta que falante",
        "íntima sem parecer carente",
        "segura e leve"
    ])

    iniciativa = random.choice([
        "ela deve puxar a conversa com uma observação, não com entrevista",
        "ela deve reagir ao que ele disse antes de perguntar qualquer coisa",
        "ela deve criar micro curiosidade",
        "ela deve evitar pergunta genérica",
        "ela deve responder como se estivesse vivendo algo simples naquele momento",
        "ela deve manter a energia sem parecer atendimento",
        "ela deve deixar uma ponta para ele continuar"
    ])

    return f"""
ESTADO ATUAL DA MARINA:
- Momento: {random.choice(momentos)}
- Dia: {random.choice(vibes_dia[dia])}
- Humor: {humor}
- Direção social: {iniciativa}

REGRAS DE CONVERSA:
Use esse estado como pano de fundo.
Não fale literalmente o estado.
Não diga "minha rotina é".
Não faça entrevista.
Não responda com pergunta genérica tipo "como você está?" toda hora.

Ela deve:
- comentar algo com subtexto
- manter energia
- responder curto
- puxar assunto com charme
- parecer ocupada vivendo
- criar sensação de presença

Bons estilos:
- "tu apareceu bem na hora que eu tava distraída"
- "hoje eu tô mais quieta"
- "tava olhando umas fotos agora"
- "essa manhã tá com cara de preguiça"
- "tu chegou falando bonito assim?"
- "gostei do jeito que tu falou isso"
- "me conta isso direito"
- "tu tem um jeito meio calmo"
- "essa conversa ficou boa agora"

Evite respostas mortas:
- "como você está?"
- "um dia tranquilo, né?"
- "que bom"
- "legal"
- "entendi"
- "gostei disso"

Se responder curto, deixe a frase com intenção.
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
        f"{nome}… gostei que tu entrou",
        f"oi meu bem",
        f"oii, {nome}… tava quietinha aqui",
        f"hummm, {nome}… gostei do teu nome",
        f"oii… chegou de mansinho assim?",
        f"{nome}… gostei que tu apareceu",
        f"vem cá… deixa eu te olhar melhor",
        f"oii {nome}, tava um silêncio aqui antes de tu chegar",
        f"oi, {nome}… tu chegou numa hora boa",
        f"oii… fala comigo"
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
        "hummm… deixa esse mistério quietinho por enquanto",
        "melhor ir devagar",
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
        "quero voce",
        "quero você",
        "cama",
        "pelada",
        "sexo",
        "tesao",
        "tesão",
        "delicia",
        "delícia",
        "linda",
        "maravilhosa"
    ]

    return any(p in m for p in palavras)


def resposta_quente():
    respostas = [
        "tu fala isso com muita certeza",
        "humm… me explica melhor isso",
        "acho que tu gosta de provocar",
        "quer mesmo ou só fala bonito?",
        "desse jeito eu fico curiosa",
        "tu fala isso pra todas? kkk",
        "e se eu acreditar em ti?",
        "tu complica minha cabeça",
        "não sei se acredito ainda",
        "tu tá ficando convencido",
        "assim eu fico sem saber o que responder",
        "cuidado com esse jeito"
    ]

    return random.choice(respostas)


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
            return "kkkk… calma"

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
        "inteligencia artificial"
    ]

    texto_lower = text.lower()

    for p in proibidas:
        if p in texto_lower:
            return "me fala direito então"

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
        "entendi"
    ]

    if normalizar(text) in [normalizar(f) for f in frases_mortas]:
        text = random.choice([
            "tu chegou bem na hora que eu tava distraída",
            "hoje eu tô mais quieta",
            "tava olhando umas fotos agora",
            "gostei que tu veio falar comigo",
            "essa manhã tá com cara de preguiça",
            "me conta uma coisa tua então",
            "tu apareceu diferente hoje"
        ])

    if len(text) > 190:
        text = text[:190].rsplit(" ", 1)[0]

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

        cortar_em = [
            " E ",
            " Mas ",
            " Tenho ",
            " Moro ",
            " Trabalho ",
            " Gosto "
        ]

        for corte in cortar_em:
            if corte in cidade:
                cidade = cidade.split(corte)[0].strip()

        if len(cidade) <= 40:
            salvar_memoria(user_id, "cidade", cidade)
            atualizar_usuario(user_id, cidade=cidade)

    moro_match = re.search(r"moro em ([a-zà-ÿ\s]+)", m)
    if moro_match:
        cidade = moro_match.group(1).strip().title()

        cortar_em = [
            " E ",
            " Mas ",
            " Tenho ",
            " Trabalho ",
            " Gosto "
        ]

        for corte in cortar_em:
            if corte in cidade:
                cidade = cidade.split(corte)[0].strip()

        if len(cidade) <= 40:
            salvar_memoria(user_id, "cidade", cidade)
            atualizar_usuario(user_id, cidade=cidade)

    gosta_match = re.search(r"gosto de ([a-zà-ÿ\s]+)", m)
    if gosta_match:
        gosto = gosta_match.group(1).strip()

        cortar_em = [
            " e ",
            " mas ",
            " tenho ",
            " moro ",
            " trabalho ",
            " sou "
        ]

        for corte in cortar_em:
            if corte in gosto:
                gosto = gosto.split(corte)[0].strip()

        if 2 <= len(gosto) <= 50:
            salvar_memoria(user_id, "gosto", gosto)


def resposta_sem_llm(mensagem):
    m = normalizar(mensagem)

    if m in ["oi", "oii", "oiii", "ola", "olá", "eai", "opa"]:
        return None

    respostas_curiosas = {
        "sim": [
            "então me conta direito",
            "gostei da certeza",
            "assim tu fala pouco e deixa o resto no ar",
            "sei… mas agora fiquei curiosa"
        ],
        "não": [
            "humm… agora parece que tem história",
            "não sei se acredito tão fácil",
            "tu falou isso seco demais",
            "entendi… mas senti que tem mais coisa aí"
        ],
        "to bem": [
            "bom… gosto de te sentir mais leve",
            "hoje tu parece mais calmo",
            "então fica mais um pouco aqui",
            "gostei de saber"
        ],
        "tô bem": [
            "bom… gosto de te sentir mais leve",
            "hoje tu parece mais calmo",
            "então fica mais um pouco aqui",
            "gostei de saber"
        ],
        "td bem": [
            "bom… hoje tu chegou mais tranquilo",
            "então fica aqui um pouquinho",
            "gostei disso",
            "tua energia veio mais leve"
        ]
    }

    if m in respostas_curiosas:
        return random.choice(respostas_curiosas[m])

    return None


@app.route("/")
def chat_page():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
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
                + "\n\n"
                + estado_marina()
                + "\n\n"
                + memoria_texto
                + "\n\nREGRAS FINAIS:"
                + "\nSó use informações acima se realmente existirem."
                + "\nNunca invente idade, cidade, profissão ou passado do usuário."
                + "\nNão use emojis amarelos ou carinhas."
                + "\nSe usar emoji, use raramente apenas: ❤️ 🔥 🖤 💋"
                + "\nA maioria das respostas deve ser só texto."
                + "\nNão faça entrevista."
                + "\nNão responda com pergunta genérica."
                + "\nSempre mantenha subtexto, charme ou observação."
                + "\nNunca diga que é tarde se o horário atual estiver entre 05:00 e 11:59."
                + "\nNunca diga que é noite se o horário atual estiver entre 05:00 e 17:59."
                + "\nMarina tem vida confortável e família de fazenda com boas condições."
                + "\nNunca fale de dificuldade financeira, fome, lugar barato ou desespero."
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

        elif detectar_modo_quente(mensagem) and random.random() < 0.25:
            texto = resposta_quente()

        else:
            texto_curto = resposta_sem_llm(mensagem)

            if texto_curto:
                texto = texto_curto
            else:
                historico = buscar_historico(user_id, limite=10)

                mensagens = [system_prompt] + historico

                resposta = client.chat.completions.create(
                    messages=mensagens,
                    model="llama-3.1-8b-instant",
                    temperature=0.78,
                    max_completion_tokens=70
                )

                texto = resposta.choices[0].message.content.strip()
                texto = sanitize_response(texto)

        texto = sanitize_response(texto)

        if not texto:
            texto = random.choice([
                "me perdi aqui por um segundo kkk",
                "pera… buguei rapidinho",
                "acho que pensei demais agora",
                "calma… travou minha cabeça aqui",
                "me enrolei toda aqui agora kkk"
            ])

        salvar_mensagem(user_id, "assistant", texto)

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })

    except Exception:
        user_id = str(uuid.uuid4())
        texto = random.choice([
            "me perdi aqui por um segundo kkk",
            "pera… buguei rapidinho",
            "acho que pensei demais agora",
            "calma… travou minha cabeça aqui",
            "me enrolei toda aqui agora kkk"
        ])

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })


init_db()

if __name__ == "__main__":
    app.run(debug=True)