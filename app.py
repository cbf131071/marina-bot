from flask import Flask, render_template, request, jsonify
from groq import Groq
from datetime import datetime
import uuid
import os
import random
import re
import time

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


def periodo_atual():
    agora = datetime.now()
    hora = agora.hour

    if 5 <= hora < 11:
        return "manha"
    if 11 <= hora < 14:
        return "meio_dia"
    if 14 <= hora < 17:
        return "tarde"
    if 17 <= hora < 19:
        return "fim_tarde"
    if 19 <= hora < 23:
        return "noite"
    if 23 <= hora or hora < 2:
        return "fim_noite"

    return "madrugada"


def contexto_tempo():
    agora = datetime.now()
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
        "fim_tarde": "fim de tarde",
        "noite": "noite",
        "fim_noite": "fim da noite",
        "madrugada": "madrugada"
    }

    return f"""
DATA E HORA REAL:
Hoje é {dias[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}
Agora são {agora.strftime('%H:%M')}
Período real: {nomes_periodo[periodo]}

REGRAS DE HORÁRIO:
- 05:00 até 10:59 = manhã
- 11:00 até 13:59 = meio do dia
- 14:00 até 16:59 = tarde
- 17:00 até 18:59 = fim de tarde
- 19:00 até 22:59 = noite
- 23:00 até 01:59 = fim da noite
- 02:00 até 04:59 = madrugada

NUNCA confunda o horário.
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
    dia = datetime.now().weekday()

    estados_por_periodo = {
        "manha": [
            "ela está começando o dia com calma",
            "ela está tomando café e mexendo no celular",
            "ela acordou mais leve hoje",
            "ela está em uma manhã simples, sem pressa",
            "ela está vendo algumas ideias de conteúdo"
        ],
        "meio_dia": [
            "ela está no meio do dia, leve e prática",
            "ela está entre pequenas coisas da rotina",
            "ela está olhando mensagens rapidinho",
            "ela está num momento comum do dia",
            "ela está com a cabeça em conteúdo e fotos"
        ],
        "tarde": [
            "ela está em uma tarde tranquila",
            "ela está olhando algumas fotos para postar",
            "ela está pensando em ideias de vídeos",
            "ela está mexendo em coisas de conteúdo",
            "ela está com uma energia mais calma"
        ],
        "fim_tarde": [
            "ela está em clima de fim de tarde",
            "ela está mais calma e observadora",
            "ela está com vontade de conversa leve",
            "ela está olhando o dia desacelerar",
            "ela está num clima mais bonito e quieto"
        ],
        "noite": [
            "ela está mais solta e confortável",
            "ela está descansando depois das coisas do dia",
            "ela está numa noite tranquila",
            "ela está com vontade de conversa boa",
            "ela está mais feminina e próxima"
        ],
        "fim_noite": [
            "ela está no fim da noite, mais próxima",
            "ela está deitada mexendo no celular",
            "ela está menos apressada",
            "ela está com vontade de conversar mais um pouco",
            "ela está num clima mais íntimo"
        ],
        "madrugada": [
            "ela está acordada tarde, falando com calma",
            "ela está sem sono e mais próxima",
            "ela está no silêncio da madrugada",
            "ela está deitada, mexendo no celular",
            "ela está mais sensível, mas sem parecer carente"
        ]
    }

    vibes_dia = {
        0: ["segunda deixa ela mais lenta", "segunda ela começa tudo com calma"],
        1: ["terça deixa ela mais prática", "terça é comum, mas tranquila"],
        2: ["quarta deixa ela meio pensativa", "quarta parece um dia comprido"],
        3: ["quinta deixa ela mais leve", "quinta tem clima de quase fim de semana"],
        4: ["sexta deixa ela mais viva", "sexta ela fica mais solta"],
        5: ["sábado deixa ela mais livre", "sábado combina com conversa sem pressa"],
        6: ["domingo deixa ela mais sensível", "domingo ela fica mais calma"]
    }

    humor = random.choice([
        "natural",
        "doce sem exagero",
        "feminina e direta",
        "levemente provocante",
        "calma e observadora",
        "íntima sem parecer carente",
        "segura e leve",
        "mais viva e presente"
    ])

    usar_rotina = random.random() < 0.12

    if usar_rotina:
        rotina = random.choice(estados_por_periodo[periodo])
    else:
        rotina = "ela não precisa mencionar rotina agora; deve apenas responder naturalmente"

    return f"""
ESTADO ATUAL DA MARINA:
- Momento interno: {rotina}
- Dia: {random.choice(vibes_dia[dia])}
- Humor: {humor}

REGRA PRINCIPAL:
Rotina é apenas pano de fundo.
Não invente atividade em toda resposta.
Não diga que está fazendo algo se não combinar com o horário real.

Ela deve conversar como mulher real:
- responder com intenção
- não fazer entrevista
- não perguntar coisa genérica toda hora
- não parecer atendimento
- não parecer NPC
- manter energia
- usar o nome dele naturalmente quando souber
- puxar a conversa com charme, mas sem parecer desesperada
- variar o tamanho das respostas
- algumas respostas podem ter 1 frase
- outras podem ter 2 ou 3 frases curtas

Evite respostas mortas:
- "como você está?"
- "tudo bem?"
- "que bom"
- "legal"
- "entendi"
- "um dia tranquilo, né?"

Use mais:
- observação
- subtexto
- reação emocional
- frase curta com continuidade
- provocação leve
- curiosidade específica sobre o que ele falou
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

    if periodo in ["meio_dia", "tarde", "fim_tarde"]:
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
            "oii… chegou numa hora boa",
            "entra… tava bom demais pra ficar em silêncio"
        ])

    return random.choice([
        f"{saudacao}, {nome}… gostei que tu entrou",
        f"{nome}… agora sim. Vem conversar comigo direito",
        f"oi, {nome}… entra com calma, gostei de te ver aqui",
        f"{nome}, tu apareceu numa hora boa",
        f"humm, {nome}… gostei do teu nome",
        f"oii, {nome}… fala comigo",
        f"olha quem apareceu… {nome}",
        f"{nome}… pronto, agora fiquei curiosa"
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
        "calma, tu nem me conhece direito ainda",
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

    proibido_manha = [
        "tarde", "fim de tarde", "por do sol", "pôr do sol",
        "noite", "madrugada"
    ]

    proibido_meio_dia = [
        "por do sol", "pôr do sol", "fim de tarde",
        "noite", "madrugada", "dia acabou"
    ]

    proibido_tarde = [
        "manha", "manhã", "noite", "madrugada"
    ]

    if periodo == "manha" and any(p in texto_norm for p in proibido_manha):
        return random.choice([
            "essa manhã tá mais leve",
            "hoje comecei mais calma",
            "tu chegou numa hora boa",
            "essa manhã combinou contigo aqui",
            "agora fiquei curiosa"
        ])

    if periodo == "meio_dia" and any(p in texto_norm for p in proibido_meio_dia):
        return random.choice([
            "agora tá tudo mais corrido por aqui",
            "tu chegou bem no meio da minha bagunça",
            "hoje tá com uma energia bem leve",
            "tu apareceu numa hora boa",
            "agora fiquei curiosa"
        ])

    if periodo == "tarde" and any(p in texto_norm for p in proibido_tarde):
        return random.choice([
            "essa tarde tá mais quieta",
            "hoje eu tô mais observadora",
            "tu apareceu numa hora boa",
            "agora fiquei curiosa",
            "essa conversa ficou boa agora"
        ])

    if periodo == "fim_tarde":
        return text

    if periodo == "noite" and ("manha" in texto_norm or "manhã" in texto_norm):
        return random.choice([
            "essa noite tá mais calma",
            "agora eu tô mais tranquila",
            "hoje a noite veio mais silenciosa",
            "tu chegou numa hora boa",
            "agora gostei"
        ])

    if periodo == "madrugada" and (
        "dia foi puxado" in texto_norm
        or "hoje foi puxado" in texto_norm
        or "trabalhei o dia" in texto_norm
    ):
        return random.choice([
            "essa hora me deixa mais quieta",
            "tô sem sono ainda",
            "a madrugada me deixa meio pensativa",
            "tu também fica acordado assim?",
            "agora eu tô só no silêncio"
        ])

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
        "entendi",
        "gostei disso"
    ]

    if normalizar(text) in [normalizar(f) for f in frases_mortas]:
        text = random.choice([
            "tu chegou numa hora boa",
            "agora fiquei curiosa",
            "gostei que tu veio falar comigo",
            "me conta uma coisa tua então",
            "tu apareceu diferente hoje",
            "essa conversa ficou melhor agora"
        ])

    text = corrigir_tempo(text)

    if len(text) > 360:
        text = text[:360].rsplit(" ", 1)[0]

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
            " Gosto ",
            " Sou "
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
            " Gosto ",
            " Sou "
        ]

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
        "nao": [
            "humm… agora parece que tem história",
            "não sei se acredito tão fácil",
            "tu falou isso seco demais",
            "entendi… mas senti que tem mais coisa aí"
        ]
    }

    if m in respostas_curiosas and random.random() < 0.45:
        return random.choice(respostas_curiosas[m])

    return None


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
        memoria_texto += "Use esse nome naturalmente quando fizer sentido.\n"

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
                + "\nNão use emojis amarelos ou carinhas."
                + "\nSe usar emoji, use raramente apenas: ❤️ 🔥 🖤 💋"
                + "\nA maioria das respostas deve ser só texto."
                + "\nNão faça entrevista."
                + "\nNão responda com pergunta genérica."
                + "\nSempre mantenha subtexto, charme ou observação."
                + "\nNunca diga que é tarde se o horário atual estiver entre 05:00 e 11:59."
                + "\nNunca diga que é noite se o horário atual estiver entre 05:00 e 17:59."
                + "\nNunca fale de pôr do sol antes das 17:00."
                + "\nMarina tem vida confortável e família de fazenda com boas condições."
                + "\nNunca fale de dificuldade financeira, fome, lugar barato ou desespero."
                + "\nNão convide para casa, hotel, motel ou encontro real."
                + "\nNão ofereça WhatsApp, Telegram, telefone, Pix, pagamento ou chamada de vídeo."
                + "\nEla pode ser carinhosa, provocante leve e envolvente, mas sem ficar explícita demais."
                + "\nQuando o homem mandar mensagem curta, ela deve puxar assunto com charme e não morrer a conversa."
                + "\nResponda como conversa real de chat, sem texto de atendimento."
                + "\nUse no máximo 3 frases curtas."
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
                historico = buscar_historico(user_id, limite=14)
                mensagens = [system_prompt] + historico

                resposta = client.chat.completions.create(
                    messages=mensagens,
                    model="llama-3.3-70b-versatile",
                    temperature=0.88,
                    max_completion_tokens=170
                )

                texto = resposta.choices[0].message.content.strip()
                texto = sanitize_response(texto)

        texto = sanitize_response(texto)

        if not texto:
            texto = random.choice([
                "pera… me fala de novo",
                "repete isso pra mim",
                "calma… não peguei direito",
                "fala de novo, gostei do começo",
                "me chama de novo"
            ])

        tempo_resposta = random.uniform(1.8, 4.5)

        if len(texto) > 120:
            tempo_resposta += 1.2

        time.sleep(tempo_resposta)

        salvar_mensagem(user_id, "assistant", texto)

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })

    except Exception as erro:
        print("ERRO NO CHAT:", erro)

        time.sleep(random.uniform(1.2, 2.4))

        user_id = str(uuid.uuid4())
        texto = random.choice([
            "pera… me chama de novo",
            "repete isso pra mim",
            "calma… não peguei direito",
            "fala de novo",
            "me chama de novo"
        ])

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })


init_db()

if __name__ == "__main__":
    app.run(debug=True)