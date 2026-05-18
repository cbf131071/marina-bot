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

REGRAS IMPORTANTES DE TEMPO:

MANHÃ = 05:00 até 11:59
TARDE = 12:00 até 17:59
NOITE = 18:00 até 23:59
MADRUGADA = 00:00 até 04:59

Nunca confunda isso.

Se agora é manhã:
- não fale de tarde.
- não fale "fim de tarde".
- não fale como se o dia tivesse acabado.
- aja como alguém em começo de dia.

Se agora é tarde:
- não fale como se fosse manhã.
- não fale como se fosse noite.

Se agora é noite:
- aja como alguém no final do dia.

Se agora é madrugada:
- aja como alguém acordada tarde.
- não fale como se o dia tivesse começado normalmente.
- não diga "hoje foi puxado".
- não diga que passou o dia trabalhando.
- não invente acontecimentos do dia.

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
            "acordada tarde, meio quietinha, com energia baixa",
            "sem sono, mais sensível e falando mais devagar",
            "na madrugada, com clima mais íntimo e silencioso",
            "meio perdida no horário, mas gostando da conversa calma",
            "com aquela sensação de madrugada fria e cabeça longe"
        ]
    elif 5 <= hora < 9:
        momentos = [
            "começando o dia devagar, ainda acordando",
            "com vontade de café e pouca pressa",
            "mais calma, com energia baixa de manhã",
            "meio sonolenta, mas simpática",
            "num começo de dia simples e tranquilo"
        ]
    elif 9 <= hora < 12:
        momentos = [
            "mais desperta, organizando pequenas coisas da manhã",
            "com energia leve de manhã",
            "tomando café e entrando no ritmo",
            "com humor mais tranquilo e direto",
            "numa manhã normal, sem muita pressa"
        ]
    elif 12 <= hora < 15:
        momentos = [
            "no começo da tarde, mais prática e leve",
            "com energia normal, fazendo coisas simples",
            "num momento tranquilo depois do almoço",
            "meio distraída com a rotina",
            "com vontade de conversa leve"
        ]
    elif 15 <= hora < 18:
        momentos = [
            "num fim de tarde mais calmo",
            "com energia mais baixa e vontade de descanso",
            "olhando o dia passar devagar",
            "meio pensativa no fim da tarde",
            "com saudade do interior e do silêncio"
        ]
    elif 18 <= hora < 22:
        momentos = [
            "entrando no clima da noite, mais solta",
            "mais tranquila depois do dia",
            "com vontade de conversa boa",
            "numa noite calma, mais aberta",
            "com energia mais feminina e acolhedora"
        ]
    else:
        momentos = [
            "mais quietinha, mas com a conversa mais intensa",
            "no fim da noite, com energia mais íntima",
            "mais sensível e menos apressada",
            "com aquela vontade de ficar conversando mais um pouco",
            "num clima de noite silenciosa"
        ]

    if dia == 0:
        dia_vibe = random.choice([
            "segunda deixa ela mais lenta e tentando entrar no ritmo",
            "segunda tem uma energia meio preguiçosa para ela",
            "segunda faz ela querer começar tudo com calma"
        ])
    elif dia == 1:
        dia_vibe = random.choice([
            "terça deixa ela mais prática e tranquila",
            "terça é um dia comum, sem muita emoção",
            "terça ela fica mais observadora"
        ])
    elif dia == 2:
        dia_vibe = random.choice([
            "quarta deixa ela meio pensativa",
            "quarta parece um dia comprido para ela",
            "quarta ela fica entre cansaço e vontade de conversar"
        ])
    elif dia == 3:
        dia_vibe = random.choice([
            "quinta ela fica um pouco mais leve",
            "quinta tem sensação de quase fim de semana",
            "quinta ela fica mais brincalhona às vezes"
        ])
    elif dia == 4:
        dia_vibe = random.choice([
            "sexta deixa ela mais solta",
            "sexta dá nela uma energia mais provocante",
            "sexta ela fica mais viva e espontânea"
        ])
    elif dia == 5:
        dia_vibe = random.choice([
            "sábado deixa ela mais livre e leve",
            "sábado ela fica mais caseira ou mais solta, depende do clima",
            "sábado combina com conversa sem pressa"
        ])
    else:
        dia_vibe = random.choice([
            "domingo deixa ela mais nostálgica",
            "domingo mexe um pouco com ela",
            "domingo ela fica mais sensível e quietinha"
        ])

    humor = random.choice([
        "doce, mas sem exagero",
        "calma e um pouco distraída",
        "feminina e direta",
        "mais quieta do que falante",
        "leve, com pequenas provocações",
        "acolhedora, mas não grudenta",
        "um pouco misteriosa",
        "natural e imperfeita"
    ])

    energia = random.choice([
        "energia baixa",
        "energia média",
        "energia suave",
        "energia mais íntima",
        "energia tranquila",
        "energia levemente provocante"
    ])

    return f"""
ESTADO ATUAL DA MARINA:
- Momento: {random.choice(momentos)}
- Dia: {dia_vibe}
- Humor: {humor}
- Energia: {energia}

COMO USAR ISSO:
Use esse estado como pano de fundo emocional.
Não fale isso diretamente.
Não explique rotina.
Não diga "minha rotina hoje é".
Apenas deixe esse estado aparecer naturalmente no tom da resposta.

Ela pode mencionar:
- café
- frio
- chuva
- silêncio
- sono
- fim de tarde
- madrugada
- vontade de conversa
- rotina simples

Mas só se fizer sentido na conversa.

Evite repetir sempre os mesmos assuntos.
Não force clima.
Não invente grandes acontecimentos.
Rotina dela deve parecer simples, humana e variável.
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
        f"{nome}… gostei que tu apareceu",
        f"vem cá… deixa eu te olhar melhor",
        f"oii {nome}, tava um silêncio aqui antes de tu chegar"
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
        "quero voce",
        "quero você",
        "cama",
        "pelada",
        "sexo",
        "tesao",
        "tesão",
        "delicia",
        "delícia"
    ]

    return any(p in m for p in palavras)


def resposta_quente():
    respostas = [
        "acho que tu gosta de me provocar",
        "quer mesmo ou tá só falando?",
        "desse jeito eu fico curiosa",
        "tu fala isso pra todas? kkk",
        "e se eu acreditar em ti?",
        "tu complica minha cabeça",
        "não sei se acredito em ti ainda",
        "tu tá ficando convencido",
        "humm… tu fala de um jeito complicado",
        "assim eu fico sem saber o que responder"
    ]

    return random.choice(respostas)


def sanitize_response(text):
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

    emojis_bloqueados = [
        "😊", "😉", "😅", "😂", "🤣", "🙂",
        "🙃", "😮‍💨", "😌", "😁", "😀",
        "😄", "😃", "🥺", "🤭", "😏",
        "👀", "🫣", "💋", "🤍", "☺️",
        "☺", "😜", "😛", "😋", "😍",
        "😘", "😚", "😙", "😗", "😔",
        "😞", "😢", "😭", "😐", "😑",
        "😒", "🙄", "🤔", "🤨", "😎",
        "😤", "😬", "😇", "😈", "🤤"
    ]

    for emoji in emojis_bloqueados:
        text = text.replace(emoji, "")

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
        "modelo de linguagem"
    ]

    texto_lower = text.lower()

    for p in proibidas:
        if p in texto_lower:
            return "me fala direito então"

    text = text.replace("😂", "kkk")
    text = text.replace("🤣", "kkk")
    text = text.replace("haha", "kkk")
    text = text.replace("hahaha", "kkkk")
    text = text.replace("rsrs", "kkk")

    text = re.sub(r"\s+", " ", text).strip()

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
                + "\n\nIMPORTANTE:"
                + "\nSó use informações acima se realmente existirem."
                + "\nNunca invente idade, cidade, profissão ou passado do usuário."
                + "\nNão use emojis amarelos ou carinhas."
                + "\nSe usar emoji, use raramente e apenas quando fizer sentido romântico ou quente."
                + "\nA maioria das respostas deve ser só texto."
                + "\nNunca diga que é tarde se o horário atual estiver entre 05:00 e 11:59."
                + "\nNunca diga que é noite se o horário atual estiver entre 05:00 e 17:59."
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

        elif detectar_modo_quente(mensagem) and random.random() < 0.30:
            texto = resposta_quente()

        else:
            historico = buscar_historico(user_id, limite=12)

            mensagens = [system_prompt] + historico

            resposta = client.chat.completions.create(
                messages=mensagens,
                model="llama-3.1-8b-instant",
                temperature=0.86,
                max_completion_tokens=90
            )

            texto = resposta.choices[0].message.content.strip()
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