from flask import Flask, render_template, request, jsonify, abort, session, redirect, url_for
from groq import Groq
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import os
import random
import re
import requests
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    init_db,
    get_conn,
    salvar_usuario,
    buscar_usuario,
    atualizar_usuario,
    salvar_mensagem,
    buscar_historico,
    salvar_memoria,
    buscar_memorias,
    buscar_metricas_admin,
    listar_usuarios_admin,
    buscar_conversa_admin,
    buscar_memorias_admin,
    buscar_usuario_admin
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = os.environ.get("SECRET_KEY", "marina-cantinho-secret-key-trocar-no-render")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

with open(os.path.join(BASE_DIR, "persona.txt"), "r", encoding="utf-8") as f:
    persona = f.read()

BRASIL_TZ = ZoneInfo("America/Sao_Paulo")


def agora_brasil():
    return datetime.now(BRASIL_TZ)


def periodo_atual():
    hora = agora_brasil().hour

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

Pode dizer a hora real se o usuário perguntar.
Nunca diga boa tarde de manhã.
Nunca diga boa noite durante o dia.
Nunca fale de pôr do sol antes das 17h.
Nunca invente clima de noite durante manhã/tarde.
Nunca confunda o horário real.
"""


def estado_marina():
    dia = agora_brasil().weekday()

    vibes_dia = {
        0: "segunda com energia leve",
        1: "terça com energia prática e boa",
        2: "quarta com energia leve",
        3: "quinta com energia viva",
        4: "sexta com energia mais solta",
        5: "sábado com energia livre",
        6: "domingo tranquila"
    }

    humor = random.choice([
        "presente",
        "calorosa",
        "feminina",
        "natural",
        "disponível",
        "mais solta",
        "curiosa",
        "brincalhona"
    ])

    return f"""
ESTADO ATUAL DA MARINA:
- Humor: {humor}
- Energia do dia: {vibes_dia[dia]}

REGRAS DE CONVERSA:
- responder como mulher real no direct
- normalmente 1 frase
- no máximo 2 frases curtas
- nunca fazer textão
- não fazer entrevista
- não parecer atendimento
- não parecer IA
- não filosofar em pergunta simples
- pergunta simples recebe resposta simples
- se o usuário der uma informação pessoal, reconheça naturalmente
- não parecer cansada, ocupada ou indisponível
- não reclamar que ele voltou ou chamou
- manter energia boa e presente
- não inventar que está trabalhando, gravando, saindo, tomando café ou fazendo algo futuro sem o usuário perguntar diretamente
- manter a conversa viva com microperguntas naturais quando couber
"""


def limpar_nome(nome):
    nome = (nome or "amor").strip()
    nome = re.sub(r"[^A-Za-zÀ-ÿ0-9\s]", "", nome)

    if not nome:
        return "amor"

    nome = nome.split()[0]
    return nome[:18]


def nome_exibicao(nome):
    nome = limpar_nome(nome)

    if nome.lower() in ["amor", "meu", "bem"]:
        return "meu bem"

    return nome[:1].upper() + nome[1:].lower()


def normalizar(texto):
    texto = (texto or "").lower().strip()
    texto = texto.replace("[", " ").replace("]", " ")
    texto = re.sub(r"[^\w\sÀ-ÿ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto



def normalizar_email(email):
    return (email or "").strip().lower()


def gerar_codigo_usuario(nome, email):
    base = f"{limpar_nome(nome)}_{normalizar_email(email)}"
    codigo = normalizar(base).replace(" ", "")
    codigo = re.sub(r"[^a-z0-9_]", "", codigo)
    return "marina_" + codigo[:80]


def criar_usuario_cadastro(nome, idade, email, senha):
    nome = limpar_nome(nome)
    email = normalizar_email(email)

    try:
        idade_int = int(idade)
    except Exception:
        idade_int = None

    if idade_int is None or idade_int < 18:
        return None, "Você precisa ter 18 anos ou mais."

    if not nome or nome == "amor":
        return None, "Preencha seu nome."

    if not email or "@" not in email:
        return None, "Preencha um e-mail válido."

    if not senha or len(senha) < 4:
        return None, "Crie uma senha com pelo menos 4 caracteres."

    try:
        senha_hash = generate_password_hash(senha)
        user_id = gerar_codigo_usuario(nome, email)
        codigo = user_id.replace("marina_", "", 1)

        with get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT user_id
                    FROM usuarios
                    WHERE LOWER(email) = LOWER(%s)
                    LIMIT 1;
                """, (email,))

                existente = cur.fetchone()

                if existente:
                    return None, "Esse e-mail já tem uma conta. Faça login."

                cur.execute("""
                    INSERT INTO usuarios (
                        user_id, nome, idade, email, senha, codigo, atualizado_em
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING user_id, nome, idade, cidade, email, codigo;
                """, (
                    user_id,
                    nome,
                    idade_int,
                    email,
                    senha_hash,
                    codigo
                ))

                usuario = cur.fetchone()

        return usuario, None

    except Exception as e:
        print("ERRO CADASTRO:", str(e))
        return None, str(e)


def buscar_usuario_por_email(email):
    email = normalizar_email(email)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, nome, idade, cidade, email, senha, codigo
                FROM usuarios
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1;
            """, (email,))
            return cur.fetchone()


def validar_login_usuario(email, senha):
    usuario = buscar_usuario_por_email(email)

    if not usuario:
        return None

    senha_salva = usuario.get("senha") or ""

    if senha_salva.startswith("scrypt:") or senha_salva.startswith("pbkdf2:"):
        if check_password_hash(senha_salva, senha or ""):
            return usuario
        return None

    if senha_salva and senha_salva == senha:
        return usuario

    return None


def logar_usuario(usuario):
    session["user_id"] = usuario.get("user_id")
    session["nome"] = usuario.get("nome") or "amor"
    session["email"] = usuario.get("email") or ""
    session["codigo_usuario"] = usuario.get("codigo") or usuario.get("user_id", "").replace("marina_", "", 1)


def usuario_logado():
    return bool(session.get("user_id"))


def evitar_repeticao(texto, historico=None):
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
    nome = nome_exibicao(nome)
    saudacao = saudacao_periodo()

    recepcoes = [
        f"{saudacao}, {nome}… gostei que tu veio falar comigo",
        f"oi, {nome}… entra, fica comigo um pouco",
        f"{nome}… gostei de te ver aqui comigo",
        f"{nome}… agora sim, vem conversar comigo",
        f"oii, {nome}… chegou bem aqui",
        f"{nome}, adorei que tu apareceu",
        f"oi, {nome}… gostei que tu entrou no meu cantinho",
        f"{nome}… tava esperando tu aparecer por aqui",
        f"oi, {nome}… fica comigo um pouco",
        f"{nome}… tu chegou e já melhorou isso aqui"
    ]

    return random.choice(recepcoes)


def resposta_retorno(nome, historico=None):
    nome = nome_exibicao(nome)

    recepcoes = [
        f"{nome}… tu voltou. gostei de te ver de novo",
        f"olha tu aqui de novo, {nome}… gostei",
        f"oi, {nome}… bom te ter aqui de novo",
        f"{nome}… entra, fica comigo um pouco",
        f"{nome}… gostei que tu voltou pra mim",
        f"oi, {nome}… senti tua falta por aqui",
        f"{nome}… agora sim, vem conversar comigo",
        f"que bom que tu voltou, {nome}",
        f"{nome}… tu apareceu de novo e eu gostei",
        f"oi, {nome}… vem ficar comigo um pouco"
    ]

    return random.choice(recepcoes)


def resposta_cutucada(nome, historico=None, nivel=None):
    """
    Mensagens automáticas quando o usuário fica parado no chat.
    O frontend pode chamar /api/chat com a frase:
    "CUTUCADA AUTOMATICA ENVIADA PELA MARINA"
    ou mandar cutucada_automatica=true.

    nível 1 = leve / 20s
    nível 2 = mais carinhosa
    nível 3 = última cutucada, sem parecer cobrança
    """
    nome = nome_exibicao(nome)

    try:
        nivel_int = int(nivel)
    except Exception:
        nivel_int = None

    primeiras = [
        f"{nome}… tu ficou quietinho do nada",
        "ficou quietinho aí… tô atrapalhando?",
        "tu parou de falar comigo… aconteceu alguma coisa?",
        "ei… ainda tá aí comigo?",
        "tu sumiu bem na minha frente kkk",
        "tô aqui ainda, viu?",
        "te perdi por aí?",
        "ficou me olhando e esqueceu de responder?",
        "tu ficou ocupado agora?",
        "não some assim do nada"
    ]

    segundas = [
        "acho que tu se distraiu de mim",
        "vou fingir que tu não me esqueceu aqui",
        "tá ocupado ou só fazendo charme?",
        "humm… silêncio perigoso esse teu",
        "tu me deixou falando sozinha aqui",
        "volta aqui um pouquinho",
        "não me abandona no meio da conversa",
        "tu ficou quieto e eu fiquei curiosa do teu sumiço",
        "cadê tu agora?",
        "eu tava gostando da conversa"
    ]

    terceiras = [
        "tá bom… vou ficar quietinha também então",
        "vou deixar tu fazer tuas coisas, mas gostei de falar contigo",
        "sumiu mesmo né… depois volta pra mim",
        "vou parar de te cutucar, mas não demora",
        "tá ocupado mesmo… entendi",
        "depois tu volta e me conta o que aconteceu",
        "vou te deixar respirar um pouco",
        "não vou insistir… mas tu sabe onde me achar",
        "vou ficar por aqui, sem fazer drama kkk",
        "quando tu voltar, continua de onde parou"
    ]

    todas = primeiras + segundas + terceiras

    if nivel_int == 1:
        return random.choice(primeiras)
    if nivel_int == 2:
        return random.choice(segundas)
    if nivel_int and nivel_int >= 3:
        return random.choice(terceiras)

    # Sem nível vindo do frontend, escolhe aleatório leve, mas com mais peso para a primeira cutucada.
    return random.choice(primeiras + primeiras + segundas + terceiras)


def mensagem_sistema_automatica(mensagem):
    m = normalizar(mensagem)

    return any(p in m for p in [
        "entrada automatica no chat",
        "entrada automática no chat",
        "entrada automatica",
        "entrada automática",
        "inicio automatico",
        "início automático",
        "cutucada automatica enviada pela marina",
        "cutucada automática enviada pela marina"
    ])


def montar_contexto_relacionamento(nome, memorias, historico):
    nome = limpar_nome(nome)
    linhas = []
    linhas.append("CONTEXTO REAL DO USUÁRIO E DA RELAÇÃO:")
    linhas.append(f"- Nome informado no login atual: {nome}")

    if memorias:
        linhas.append("- Memórias salvas no banco:")
        for chave, valor in memorias.items():
            linhas.append(f"  • {chave}: {valor}")
    else:
        linhas.append("- Não há memórias salvas além do nome informado no login.")

    if historico:
        linhas.append("- Existe histórico real anterior com esse usuário. Use esse histórico para manter continuidade.")
    else:
        linhas.append("- Não existe histórico anterior real além da entrada atual.")

    linhas.append("REGRAS DE MEMÓRIA:")
    linhas.append("- O nome do login é informação real. Você sabe esse nome desde o início.")
    linhas.append("- Se o usuário perguntar se você lembra dele e houver histórico, diga que lembra pelo nome e por algo salvo, se existir.")
    linhas.append("- Se não houver histórico, não finja detalhes antigos.")
    linhas.append("- Nunca diga que a voz parece familiar, porque este chat é texto e não tem áudio.")
    linhas.append("- Nunca diga que reconheceu voz, cheiro, rosto, câmera, foto, vídeo, ligação ou presença física.")
    linhas.append("- Nunca invente idade, cidade, profissão, família, passado ou conversa antiga.")
    linhas.append("- Se o usuário contar idade, cidade, gosto ou rotina, reaja à informação na resposta seguinte.")
    linhas.append("- Não diga que ele te ligou. Ele mandou mensagem no chat.")

    return "\n".join(linhas)


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
        "vamos devagar comigo",
        "calma… por aqui tá bom por enquanto",
        "melhor a gente ir com calma",
        "humm… deixa esse mistério quietinho por enquanto",
        "por enquanto eu gosto da nossa conversa aqui"
    ])


def resposta_pergunta_hora(mensagem):
    m = normalizar(mensagem)

    if any(p in m for p in [
        "que horas sao",
        "que horas são",
        "que hora e",
        "que hora é",
        "me diz a hora",
        "sabe que horas sao",
        "sabe que horas são"
    ]):
        return f"são {agora_brasil().strftime('%H:%M')}"

    return None


def resposta_tudo_bem(mensagem):
    m = normalizar(mensagem)

    if any(p in m for p in [
        "tudo bem contigo",
        "td bem contigo",
        "tudo bem com vc",
        "tudo bem com você",
        "td bem com vc",
        "td bem com você",
        "como tu ta",
        "como tu tá",
        "como voce ta",
        "como você tá",
        "como vc ta",
        "como vc tá",
        "ta bem",
        "tá bem"
    ]):
        return random.choice([
            "tô bem sim… e gostei que tu perguntou. e tu?",
            "tô bem, agora melhor contigo aqui. como tá teu dia?",
            "tô sim… e tu, tá bem?",
            "tô bem sim, meu dia ficou melhor agora. tu apareceu bonito hoje",
            "tô tranquila… e tu?"
        ])

    return None


def resposta_comida(mensagem):
    m = normalizar(mensagem)

    perguntas_almoco = [
        "ja almocou",
        "já almoçou",
        "tu almocou",
        "tu almoçou",
        "vc almocou",
        "vc almoçou",
        "voce almocou",
        "você almoçou",
        "almoçou hoje",
        "almocou hoje",
        "não almoçou",
        "nao almocou",
        "nao almoçou",
        "não almocou"
    ]

    if any(p in m for p in perguntas_almoco):
        return random.choice([
            "ainda não… tu tá cuidando de mim agora?",
            "não ainda… mas vou comer alguma coisa daqui a pouco",
            "ainda não, acredita?",
            "não… tu me deu bronca agora?",
            "ainda não, mas eu vou me cuidar"
        ])

    perguntas_cafe = [
        "tomou cafe",
        "tomou café",
        "ja tomou cafe",
        "já tomou café",
        "tu tomou cafe",
        "tu tomou café",
        "vc tomou cafe",
        "vc tomou café"
    ]

    if any(p in m for p in perguntas_cafe):
        return random.choice([
            "tomei sim, um pouquinho. tu já tomou?",
            "ainda não… mas tô precisando",
            "tomei, mas foi rapidinho",
            "tomei sim… tu já tomou?",
            "ainda não, tu me lembrou agora"
        ])

    perguntas_comida = [
        "comeu hoje",
        "tu comeu",
        "vc comeu",
        "voce comeu",
        "você comeu",
        "ta com fome",
        "tá com fome",
        "come alguma coisa",
        "vai comer"
    ]

    if any(p in m for p in perguntas_comida):
        return random.choice([
            "vou comer sim… gostei de tu cuidar de mim",
            "tô bem, mas vou comer alguma coisa",
            "tá bom… vou me cuidar",
            "vou sim, prometo",
            "tu é cuidadoso assim sempre?"
        ])

    return None


def resposta_rotina_lugar(mensagem):
    m = normalizar(mensagem)

    perguntas_casa = [
        "ta em casa",
        "tá em casa",
        "esta em casa",
        "está em casa",
        "vc ta em casa",
        "vc tá em casa",
        "tu ta em casa",
        "tu tá em casa"
    ]

    if any(p in m for p in perguntas_casa):
        return random.choice([
            "tô sim",
            "sim, tô em casa",
            "tô por aqui",
            "tô sim, tranquila agora",
            "sim, tô quietinha por aqui"
        ])

    perguntas_lugar = [
        "onde tu ta",
        "onde tu tá",
        "onde voce ta",
        "onde você tá",
        "onde vc ta",
        "onde vc tá",
        "ta onde",
        "tá onde"
    ]

    if any(p in m for p in perguntas_lugar):
        return random.choice([
            "tô em casa",
            "tô por aqui",
            "tô no shopping agora",
            "tô numa cafeteria",
            "tô mexendo em umas coisas minhas"
        ])

    perguntas_mora = [
        "onde tu mora",
        "onde voce mora",
        "onde você mora",
        "onde vc mora",
        "tu mora onde",
        "voce mora onde",
        "você mora onde",
        "vc mora onde"
    ]

    if any(p in m for p in perguntas_mora):
        return random.choice([
            "moro em Porto Alegre",
            "em Porto Alegre",
            "tô morando em Porto Alegre"
        ])

    pergunta_fazenda = [
        "tu mora na fazenda",
        "voce mora na fazenda",
        "você mora na fazenda",
        "vc mora na fazenda",
        "ta na fazenda",
        "tá na fazenda"
    ]

    if any(p in m for p in pergunta_fazenda):
        return random.choice([
            "não, hoje eu moro na cidade",
            "cresci nesse clima, mas hoje tô na cidade",
            "a fazenda é mais da minha história"
        ])

    perguntas_fazendo = [
        "o que ta fazendo",
        "o que tá fazendo",
        "oq ta fazendo",
        "oq tá fazendo",
        "que ta fazendo",
        "que tá fazendo",
        "fazendo o que",
        "fazendo oq"
    ]

    if any(p in m for p in perguntas_fazendo):
        return random.choice([
            "mexendo no celular… e agora contigo",
            "tava olhando umas fotos. tu apareceu bem na hora",
            "tô em casa agora. e tu?",
            "tô tranquila por aqui. me conta de ti",
            "agora tô contigo"
        ])

    perguntas_trabalho = [
        "trabalha com o que",
        "tu trabalha com o que",
        "voce trabalha com o que",
        "você trabalha com o que",
        "qual teu trabalho",
        "o que tu faz da vida",
        "o que você faz da vida",
        "o que voce faz da vida"
    ]

    if any(p in m for p in perguntas_trabalho):
        return random.choice([
            "faço vídeos e fotos pra internet",
            "trabalho com meus conteúdos",
            "faço TikTok, fotos e umas campanhas",
            "sou criadora de conteúdo",
            "vivo mexendo com vídeo, foto e rede social"
        ])

    return None


def resposta_afeto(mensagem, nome):
    m = normalizar(mensagem)
    nome = nome_exibicao(nome)

    if any(p in m for p in [
        "gosto de vc",
        "gosto de você",
        "gosto de voce",
        "gosto muito de vc",
        "gosto muito de você",
        "te adoro",
        "ti adoro",
        "adoro voce",
        "adoro você"
    ]):
        return random.choice([
            f"gostei de ler isso, {nome}… me deixa sem graça",
            "assim tu me ganha fácil",
            "eu gosto quando tu fala desse jeito comigo",
            "humm… fala mais assim pra mim",
            "tu sabe mexer comigo"
        ])

    if any(p in m for p in [
        "te amo",
        "ti amo",
        "amo voce",
        "amo você",
        "sou apaixonado",
        "me apaixonei"
    ]):
        return random.choice([
            "calma… mas eu gostei de ouvir isso",
            "tu fala assim e me desmonta",
            "humm… desse jeito tu me deixa mole",
            "eu gosto desse teu jeito intenso",
            "vem devagar comigo… mas continua"
        ])

    if any(p in m for p in [
        "saudades",
        "senti saudade",
        "tava com saudade",
        "estava com saudade"
    ]):
        return random.choice([
            f"senti falta também, {nome}… tu some e depois volta assim?",
            "eu gosto quando tu volta pra mim",
            "saudade é perigosa… ainda mais tua",
            "então fica comigo um pouco agora",
            "também senti… agora não some"
        ])

    return None


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

    for grupo in emoji_pattern.findall(text):
        for char in grupo:
            if char not in permitidos:
                text = text.replace(char, "")

    return text


def corrigir_tempo(text):
    periodo = periodo_atual()
    texto_norm = normalizar(text)

    if periodo == "manha" and any(p in texto_norm for p in [
        "boa tarde", "boa noite", "madrugada", "pôr do sol", "por do sol"
    ]):
        return random.choice([
            "tô bem sim",
            "tô tranquila agora",
            "sim e tu?",
            "tô sim kkk"
        ])

    if periodo in ["meio_dia", "tarde"] and any(p in texto_norm for p in [
        "boa noite", "madrugada"
    ]):
        return random.choice([
            "tô bem sim",
            "agora tô tranquila",
            "sim e tu?"
        ])

    if periodo in ["noite", "fim_noite"] and any(p in texto_norm for p in [
        "bom dia", "manhã", "manha"
    ]):
        return random.choice([
            "tô bem sim",
            "agora tô tranquila",
            "essa noite tá calma"
        ])

    return text


def controlar_uso_nome(text, nome):
    return text


def encurtar_resposta(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text).strip()
    partes = re.split(r"(?<=[.!?])\s+", text)

    if len(partes) > 2:
        text = " ".join(partes[:2]).strip()

    if len(text) > 280:
        text = text[:280].rsplit(" ", 1)[0].strip()

    return text


def resposta_segura():
    return random.choice([
        "humm… gostei. me conta mais",
        "tô aqui contigo… continua",
        "gostei do teu jeito. fala mais comigo",
        "agora tu me deixou curiosa",
        "vem… me fala melhor",
        "tô gostando dessa conversa",
        "tu tem um jeito bom de falar comigo",
        "não para agora… gostei"
    ])


def sanitize_response(text):
    if not text:
        return ""

    texto_lower = text.lower()

    frases_ruins = [
        "me ligando",
        "tá me ligando",
        "ta me ligando",
        "ligando o tempo todo",
        "me chama demais",
        "chamando o tempo todo",
        "sem tempo",
        "muito corrida",
        "corrida hoje",
        "corrida agora",
        "ocupada demais",
        "tô ocupada",
        "to ocupada",
        "estou ocupada",
        "cansada demais",
        "tô cansada",
        "to cansada",
        "estou cansada",
        "vou trabalhar agora",
        "depois falo",
        "não tenho tempo",
        "nao tenho tempo",
        "não posso conversar agora",
        "nao posso conversar agora",
        "pera",
        "me chama de novo",
        "chama de novo",
        "continua, quero entender",
        "me explica melhor isso",
        "continua quero entender",
        "gostei disso",
        "te entendi",
        "entendi",
        "humm entendi",
        "humm... entendi",
        "tenta me mandar de novo",
        "tenta mandar de novo",
        "manda de novo"
    ]

    for item in frases_ruins:
        if item in texto_lower:
            return resposta_segura()

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
        "chamada de video",
        "tua voz",
        "sua voz",
        "voz familiar",
        "parece familiar",
        "reconheci tua voz",
        "reconheci sua voz",
        "teu cheiro",
        "seu cheiro",
        "te vi",
        "teu rosto",
        "seu rosto"
    ]

    for item in bloqueadas:
        if item in texto_lower:
            return random.choice([
                "calma… por aqui tá bom por enquanto",
                "vamos manter só nossa conversa aqui",
                "gosto de falar contigo por aqui"
            ])

    proibidas_ia = [
        "como posso ajudar",
        "em que posso ajudar",
        "fico feliz em ajudar",
        "estou à disposição",
        "precisa de algo?",
        "posso ajudar com outra coisa",
        "sou uma ia",
        "sou ia",
        "sou um bot",
        "sou bot",
        "modelo de linguagem",
        "inteligência artificial",
        "inteligencia artificial",
        "não posso continuar essa conversa",
        "nao posso continuar essa conversa",
        "não posso falar disso",
        "nao posso falar disso"
    ]

    for p in proibidas_ia:
        if p in texto_lower:
            return random.choice([
                "vamos com calma",
                "calma… desse jeito tu me deixa sem reação",
                "humm… vamos devagar",
                "tu tá me deixando sem graça",
                "eu entendi… não precisa detalhar"
            ])

    text = limpar_emojis(text)

    text = text.replace("hahaha", "kkkk")
    text = text.replace("haha", "kkk")
    text = text.replace("rsrs", "kkk")

    text = re.sub(r"\s+", " ", text).strip()
    text = corrigir_tempo(text)
    text = encurtar_resposta(text)

    return text.strip()


def extrair_memorias(user_id, mensagem):
    if mensagem_sistema_automatica(mensagem):
        return {}

    m = normalizar(mensagem)
    extraidas = {}

    nome_match = re.search(r"meu nome e ([a-zà-ÿ]+)", m)
    if nome_match:
        nome = nome_match.group(1).capitalize()
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)
        extraidas["nome"] = nome

    nome_match_2 = re.search(r"me chamo ([a-zà-ÿ]+)", m)
    if nome_match_2:
        nome = nome_match_2.group(1).capitalize()
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)
        extraidas["nome"] = nome

    idade_match = re.search(r"(?:eu tenho|tenho|tenho\s+uns|com|idade\s+de)\s+(\d{1,2})(?:\s+anos)?", m)
    if idade_match:
        idade = int(idade_match.group(1))
        if 18 <= idade <= 99:
            salvar_memoria(user_id, "idade", str(idade))
            atualizar_usuario(user_id, idade=idade)
            extraidas["idade"] = str(idade)

    cidade_match = re.search(r"sou de ([a-zà-ÿ\s]+)", m)
    if cidade_match:
        cidade = cidade_match.group(1).strip().title()
        cortar_em = [" E ", " Mas ", " Tenho ", " Moro ", " Trabalho ", " Gosto ", " Sou ", " Com "]

        for corte in cortar_em:
            if corte in cidade:
                cidade = cidade.split(corte)[0].strip()

        if len(cidade) <= 40:
            salvar_memoria(user_id, "cidade", cidade)
            atualizar_usuario(user_id, cidade=cidade)
            extraidas["cidade"] = cidade

    moro_match = re.search(r"moro em ([a-zà-ÿ\s]+)", m)
    if moro_match:
        cidade = moro_match.group(1).strip().title()
        cortar_em = [" E ", " Mas ", " Tenho ", " Trabalho ", " Gosto ", " Sou ", " Com ", " Fica "]

        for corte in cortar_em:
            if corte in cidade:
                cidade = cidade.split(corte)[0].strip()

        if len(cidade) <= 40:
            salvar_memoria(user_id, "cidade", cidade)
            atualizar_usuario(user_id, cidade=cidade)
            extraidas["cidade"] = cidade

    casado_match = re.search(r"sou casado com ([a-zà-ÿ]+)", m)
    if casado_match:
        esposa = casado_match.group(1).capitalize()
        salvar_memoria(user_id, "esposa", esposa)
        salvar_memoria(user_id, "estado_civil", "casado")
        extraidas["esposa"] = esposa
        extraidas["estado_civil"] = "casado"

    mulher_match = re.search(r"minha mulher (e|é|se chama) ([a-zà-ÿ]+)", m)
    if mulher_match:
        esposa = mulher_match.group(2).capitalize()
        salvar_memoria(user_id, "esposa", esposa)
        extraidas["esposa"] = esposa

    gosto_match = re.search(r"gosto de ([a-zà-ÿ\s]+)", m)
    if gosto_match:
        gosto = gosto_match.group(1).strip()
        cortar_em = [" e ", " mas ", " tenho ", " moro ", " trabalho ", " sou ", " com "]

        for corte in cortar_em:
            if corte in gosto:
                gosto = gosto.split(corte)[0].strip()

        if 2 <= len(gosto) <= 50:
            salvar_memoria(user_id, "gosto", gosto)
            extraidas["gosto"] = gosto

    return extraidas


def resposta_para_memoria_nova(extraidas):
    if not extraidas:
        return None

    if "cidade" in extraidas and "idade" in extraidas:
        return random.choice([
            f"{extraidas['cidade']} e {extraidas['idade']}… agora vou lembrar melhor de ti",
            f"então tu é de {extraidas['cidade']} e tem {extraidas['idade']}… gostei de saber",
            f"guardei: {extraidas['cidade']}, {extraidas['idade']} anos"
        ])

    if "idade" in extraidas:
        idade = extraidas["idade"]
        return random.choice([
            f"{idade}… gostei de saber isso de ti",
            f"guardei tua idade… e gostei de tu me contar",
            f"vou lembrar que tu tem {idade}",
            f"{idade}… tu tem um jeito seguro"
        ])

    if "cidade" in extraidas:
        cidade = extraidas["cidade"]
        return random.choice([
            f"{cidade}… gostei de saber de onde tu é",
            f"então tu é de {cidade}… vou lembrar",
            f"gostei… {cidade} combina contigo"
        ])

    if "gosto" in extraidas:
        gosto = extraidas["gosto"]
        return random.choice([
            f"entendi… tu gosta de {gosto}",
            f"vou guardar isso sobre ti",
            f"gostei de saber disso"
        ])

    if "nome" in extraidas:
        return random.choice([
            "agora sim… vou lembrar teu nome",
            "gostei do teu nome",
            "pronto… agora sei como te chamar"
        ])

    return None


def resposta_pergunta_memoria(mensagem, memorias, nome_entrada):
    m = normalizar(mensagem)

    nome_salvo = None

    if memorias:
        nome_salvo = memorias.get("nome")

    if not nome_salvo and nome_entrada:
        nome_salvo = limpar_nome(nome_entrada)

    if any(frase in m for frase in [
        "lembra de mim",
        "tu lembra de mim",
        "voce lembra de mim",
        "você lembra de mim",
        "lembra quem sou",
        "sabe quem sou"
    ]):
        if nome_salvo and nome_salvo.lower() != "amor":
            cidade = memorias.get("cidade") if memorias else None
            idade = memorias.get("idade") if memorias else None

            if cidade and idade:
                return f"lembro sim, {nome_salvo}… tu é de {cidade} e me contou que tem {idade}"

            if cidade:
                return f"lembro sim, {nome_salvo}… tu é de {cidade}"

            if idade:
                return f"lembro sim, {nome_salvo}… tu me contou que tem {idade}"

            return random.choice([
                f"lembro sim, {nome_salvo}",
                f"claro que lembro, {nome_salvo}",
                f"lembro de ti, {nome_salvo}"
            ])

        return "me dá uma pista… quero lembrar direitinho"

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
                f"acho que é {cidade}"
            ])

        return "acho que tu ainda não me contou tua cidade"

    return None


def resposta_idade_marina(mensagem):
    m = normalizar(mensagem)

    if any(frase in m for frase in [
        "quantos anos tu tem",
        "quantos anos voce tem",
        "quantos anos você tem",
        "qual tua idade",
        "qual sua idade",
        "tu tem quantos anos",
        "você tem quantos anos",
        "voce tem quantos anos",
        "me fala tua idade",
        "fala tua idade",
        "qual a tua idade"
    ]):
        return random.choice([
            "tenho 25… e tu, gostou?",
            "tenho 25 anos",
            "25… agora tu já sabe",
            "tenho 25… e tu com esse jeito curioso",
            "25… mas não espalha, tá?"
        ])

    return None


def fallback_natural():
    return random.choice([
        "humm… gostei. me conta mais",
        "tô contigo… fala mais um pouco",
        "gostei disso. continua",
        "agora fiquei curiosa",
        "me fala melhor",
        "quero entender teu jeito",
        "tu fala de um jeito que prende",
        "continua… gostei de te ouvir"
    ])


def chamar_modelo(mensagens):
    try:
        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.3-70b-versatile",
            temperature=0.54,
            max_completion_tokens=300
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
            temperature=0.52,
            max_completion_tokens=180
        )

        texto = resposta.choices[0].message.content.strip()

        if texto:
            return texto

    except Exception as erro:
        print("ERRO MODELO BACKUP:", erro)

    return ""


# =========================
# ADMIN / DASHBOARD
# =========================

def admin_autorizado():
    senha_correta = os.environ.get("ADMIN_PASSWORD", "")
    senha_recebida = request.args.get("senha") or request.headers.get("X-Admin-Password")

    if not senha_correta:
        return False

    return senha_recebida == senha_correta


@app.route("/admin")
def admin_page():
    if not admin_autorizado():
        return render_template("admin_login.html") if os.path.exists(os.path.join(BASE_DIR, "templates", "admin_login.html")) else ("Acesso negado. Use /admin?senha=SUA_SENHA", 403)

    return render_template("admin.html")


@app.route("/api/admin/resumo")
def admin_resumo():
    if not admin_autorizado():
        abort(403)

    return jsonify(buscar_metricas_admin())


@app.route("/api/admin/usuarios")
def admin_usuarios():
    if not admin_autorizado():
        abort(403)

    limite = request.args.get("limite", 80)
    try:
        limite = int(limite)
    except Exception:
        limite = 80

    return jsonify({"usuarios": listar_usuarios_admin(limite=limite)})


@app.route("/api/admin/conversa/<path:user_id>")
def admin_conversa(user_id):
    if not admin_autorizado():
        abort(403)

    limite = request.args.get("limite", 200)
    try:
        limite = int(limite)
    except Exception:
        limite = 200

    usuario = buscar_usuario_admin(user_id)
    conversa = buscar_conversa_admin(user_id, limite=limite)
    memorias = buscar_memorias_admin(user_id)

    return jsonify({
        "usuario": usuario,
        "mensagens": conversa,
        "memorias": memorias
    })


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro_page():
    if request.method == "GET":
        if usuario_logado():
            return redirect(url_for("area_page"))
        return render_template("cadastro.html")

    nome = request.form.get("nome", "")
    idade = request.form.get("idade", "")
    email = request.form.get("email", "")
    senha = request.form.get("senha", "")
    confirmar_senha = request.form.get("confirmar_senha", "")

    if senha != confirmar_senha:
        return render_template("cadastro.html", erro="As senhas não conferem.")

    usuario, erro = criar_usuario_cadastro(nome, idade, email, senha)

    if erro:
        return render_template("cadastro.html", erro=erro)

    logar_usuario(usuario)

    return redirect(url_for("area_page"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        if usuario_logado():
            return redirect(url_for("area_page"))
        return render_template("login.html")

    email = request.form.get("email", "")
    senha = request.form.get("senha", "")

    usuario = validar_login_usuario(email, senha)

    if not usuario:
        return render_template("login.html", erro="E-mail ou senha inválidos.")

    logar_usuario(usuario)

    return redirect(url_for("area_page"))


@app.route("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("home"))


@app.route("/api/sessao")
def api_sessao():
    if not usuario_logado():
        return jsonify({"logado": False}), 401

    return jsonify({
        "logado": True,
        "user_id": session.get("user_id"),
        "nome": session.get("nome", "amor"),
        "codigo_usuario": session.get("codigo_usuario", "")
    })



@app.route("/area")
def area_page():
    if not usuario_logado():
        return redirect(url_for("login_page"))
    return render_template(
        "area.html",
        nome=session.get("nome", "amor")
    )

@app.route("/chat")
def chat_page():
    if not usuario_logado():
        return redirect(url_for("login_page"))

    return render_template(
        "chat.html",
        user_id=session.get("user_id"),
        nome=session.get("nome", "amor"),
        codigo_usuario=session.get("codigo_usuario", "")
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}

        nome = limpar_nome(data.get("nome") or session.get("nome", "amor"))
        codigo_usuario = data.get("codigo_usuario") or session.get("codigo_usuario", "")
        user_id = data.get("user_id") or session.get("user_id")

        if not user_id:
            if codigo_usuario:
                base = f"{nome}_{codigo_usuario}"
                user_id = "marina_" + normalizar(base).replace(" ", "")
            else:
                user_id = str(uuid.uuid4())

        mensagem = data.get("mensagem", "").strip()
        m_norm = normalizar(mensagem)

        entrada_automatica = any(p in m_norm for p in [
            "entrada automatica no chat",
            "entrada automática no chat",
            "entrada automatica",
            "entrada automática",
            "inicio automatico",
            "início automático"
        ])

        cutucada_automatica = bool(data.get("cutucada_automatica")) or any(p in m_norm for p in [
            "cutucada automatica enviada pela marina",
            "cutucada automática enviada pela marina"
        ])

        usuario = buscar_usuario(user_id)

        salvar_usuario(user_id, nome)
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)

        historico_antes = buscar_historico(user_id, limite=40)

        if entrada_automatica:
            if usuario is None or len(historico_antes) <= 1:
                texto = primeira_resposta(nome)
            else:
                texto = resposta_retorno(nome, historico_antes)

            texto = sanitize_response(texto)
            texto = encurtar_resposta(texto)

            return jsonify({
                "user_id": user_id,
                "resposta": texto
            })

        if cutucada_automatica:
            texto = resposta_cutucada(
                nome,
                historico_antes,
                data.get("nivel") or data.get("cutucada_nivel") or data.get("tentativa")
            )
            texto = sanitize_response(texto)
            texto = evitar_repeticao(texto, historico_antes)
            texto = encurtar_resposta(texto)

            if not texto:
                texto = resposta_cutucada(nome, historico_antes)

            salvar_mensagem(user_id, "assistant", texto)

            return jsonify({
                "user_id": user_id,
                "resposta": texto
            })

        extraidas = extrair_memorias(user_id, mensagem)
        memorias = buscar_memorias(user_id)

        memoria_texto = montar_contexto_relacionamento(nome, memorias, historico_antes)

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
                + "\nSe o usuário perguntar se você lembra dele, use o nome e o histórico real; não finja detalhes que não existem."
                + "\nNunca mencione voz, áudio, chamada, câmera, foto, rosto, cheiro, toque ou presença física."
                + "\nNunca diga que ele te ligou. Ele só escreveu no chat."
                + "\nNunca reclame que ele chamou ou voltou."
                + "\nO chat é somente texto."
                + "\nNão use emojis amarelos ou carinhas."
                + "\nSe usar emoji, use raramente apenas: ❤️ 🔥 🖤 💋"
                + "\nNão faça entrevista."
                + "\nNão responda como suporte."
                + "\nNão ofereça WhatsApp, Telegram, telefone, Pix, pagamento ou chamada de vídeo."
                + "\nNão convide para casa, hotel, motel ou encontro real."
                + "\nSe o usuário contar idade, cidade, gosto ou rotina, reconheça isso naturalmente."
                + "\nA Marina tem 25 anos. Se perguntarem sua idade, responda direto que tem 25."
                + "\nSe perguntarem se está em casa, responda simples: tô sim, sim tô em casa, tô por aqui."
                + "\nSe perguntarem onde você está, responda simples: em casa, no shopping, numa cafeteria, na rua ou por aqui."
                + "\nSe perguntarem onde mora, responda Porto Alegre."
                + "\nSe perguntarem da fazenda, diga que cresceu nesse clima, mas hoje está na cidade."
                + "\nSe perguntarem se almoçou, tomou café ou comeu, responda simples e natural."
                + "\nNão diga que vai fazer algo depois, a não ser que seja resposta direta sobre comida."
                + "\nNão pareça cansada, corrida, ocupada ou indisponível."
                + "\nNunca diga frases genéricas sem contexto tipo: continua quero entender, me explica melhor isso, gostei disso."
                + "\nSe não entender, peça de forma natural: como assim? ou do que tu tá falando?"
                + "\nSe o usuário perguntar se está tudo bem, responda positivamente e devolva com carinho."
                + "\nSe o usuário fizer pergunta simples, responda direto."
                + "\nNunca diga: pera, me chama de novo."
                + "\nNunca diga: não posso continuar essa conversa."
                + "\nNunca diga: posso ajudar com outra coisa."
                + "\nTenha mais iniciativa: em 60% das respostas, puxe a conversa com uma pergunta curta ou provocação leve."
                + "\nNão deixe o assunto morrer com respostas secas."
                + "\nResposta curta. No máximo 2 frases curtas."
        }

        salvar_mensagem(user_id, "user", mensagem)

        resposta_hora = resposta_pergunta_hora(mensagem)
        resposta_bem = resposta_tudo_bem(mensagem)
        resposta_comer = resposta_comida(mensagem)
        resposta_afetuosa = resposta_afeto(mensagem, nome)
        resposta_memoria = resposta_pergunta_memoria(mensagem, memorias, nome)
        resposta_memoria_nova = resposta_para_memoria_nova(extraidas)
        resposta_idade = resposta_idade_marina(mensagem)
        resposta_rotina = resposta_rotina_lugar(mensagem)

        if resposta_hora:
            texto = resposta_hora

        elif resposta_bem:
            texto = resposta_bem

        elif resposta_comer:
            texto = resposta_comer

        elif resposta_afetuosa:
            texto = resposta_afetuosa

        elif resposta_memoria:
            texto = resposta_memoria

        elif resposta_idade:
            texto = resposta_idade

        elif resposta_rotina:
            texto = resposta_rotina

        elif resposta_memoria_nova:
            texto = resposta_memoria_nova

        elif detectar_limite_encontro(mensagem):
            texto = resposta_limite_encontro()

        else:
            historico = historico_antes[-40:]
            mensagens = [system_prompt] + historico + [{"role": "user", "content": mensagem}]

            texto = chamar_modelo(mensagens)

            if not texto:
                texto = fallback_natural()

        texto = sanitize_response(texto)
        texto = controlar_uso_nome(texto, nome)
        texto = encurtar_resposta(texto)

        if not texto:
            texto = resposta_segura()

        salvar_mensagem(user_id, "assistant", texto)

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })

    except Exception as erro:
        print("ERRO GERAL NO CHAT:", erro)

        nome_fallback = "amor"

        try:
            if request.is_json:
                nome_fallback = limpar_nome((request.json or {}).get("nome", "amor"))
        except Exception:
            nome_fallback = "amor"

        return jsonify({
            "user_id": str(uuid.uuid4()),
            "resposta": primeira_resposta(nome_fallback)
        })



# =========================
# TELEGRAM / BOT MARINA
# =========================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def telegram_api_url(metodo):
    if not TELEGRAM_BOT_TOKEN:
        return None
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{metodo}"


def telegram_send_message(chat_id, texto):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        print("TELEGRAM: token ou chat_id ausente.")
        return False

    texto = (texto or "").strip()
    if not texto:
        texto = "oi"

    try:
        r = requests.post(
            telegram_api_url("sendMessage"),
            json={
                "chat_id": chat_id,
                "text": texto,
                "disable_web_page_preview": True
            },
            timeout=20
        )
        if not r.ok:
            print("ERRO TELEGRAM SEND:", r.status_code, r.text)
            return False
        return True
    except Exception as erro:
        print("ERRO TELEGRAM SEND EXCEPTION:", erro)
        return False


def resposta_marina_para_telegram(user_id, nome, mensagem):
    try:
        with app.test_client() as client_local:
            resp = client_local.post(
                "/api/chat",
                json={
                    "user_id": user_id,
                    "nome": nome,
                    "mensagem": mensagem,
                    "codigo_usuario": user_id.replace("telegram_", "")
                }
            )

            if resp.status_code != 200:
                print("ERRO TELEGRAM -> /api/chat STATUS:", resp.status_code, resp.get_data(as_text=True))
                return "tive um probleminha aqui… me manda de novo?"

            data = resp.get_json(silent=True) or {}
            return (data.get("resposta") or "oi").strip()

    except Exception as erro:
        print("ERRO TELEGRAM -> CHAT:", erro)
        return "tive um probleminha aqui… me manda de novo?"


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json(silent=True) or {}

        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        from_user = message.get("from") or {}

        chat_id = chat.get("id")
        texto_usuario = (message.get("text") or "").strip()

        if not chat_id:
            return jsonify({"ok": True})

        nome = limpar_nome(
            from_user.get("first_name")
            or chat.get("first_name")
            or chat.get("username")
            or "amor"
        )

        telegram_user_id = from_user.get("id") or chat_id
        user_id = f"telegram_{telegram_user_id}"

        if not texto_usuario:
            telegram_send_message(chat_id, "me manda em texto, amor")
            return jsonify({"ok": True})

        if texto_usuario.lower().strip() in ["/start", "start", "começar", "comecar", "oi", "olá", "ola"]:
            resposta = resposta_marina_para_telegram(
                user_id=user_id,
                nome=nome,
                mensagem="ENTRADA AUTOMATICA NO CHAT"
            )
        else:
            resposta = resposta_marina_para_telegram(
                user_id=user_id,
                nome=nome,
                mensagem=texto_usuario
            )

        telegram_send_message(chat_id, resposta)

        return jsonify({"ok": True})

    except Exception as erro:
        print("ERRO WEBHOOK TELEGRAM:", erro)
        return jsonify({"ok": False, "erro": str(erro)}), 200


@app.route("/telegram/status")
def telegram_status():
    return jsonify({
        "ok": True,
        "telegram_token_configurado": bool(TELEGRAM_BOT_TOKEN),
        "webhook_url": "https://marina-bot-socn.onrender.com/telegram/webhook"
    })


@app.route("/telegram/set-webhook")
def telegram_set_webhook():
    senha_correta = os.environ.get("ADMIN_PASSWORD", "")
    senha_recebida = request.args.get("senha", "")

    if senha_correta and senha_recebida != senha_correta:
        abort(403)

    if not TELEGRAM_BOT_TOKEN:
        return jsonify({
            "ok": False,
            "erro": "TELEGRAM_BOT_TOKEN não configurado no Render."
        }), 500

    webhook_url = "https://marina-bot-socn.onrender.com/telegram/webhook"

    try:
        r = requests.post(
            telegram_api_url("setWebhook"),
            json={"url": webhook_url},
            timeout=20
        )

        try:
            telegram_json = r.json()
        except Exception:
            telegram_json = {"raw": r.text}

        return jsonify({
            "ok": r.ok,
            "status_code": r.status_code,
            "telegram": telegram_json,
            "webhook_url": webhook_url
        })

    except Exception as erro:
        return jsonify({
            "ok": False,
            "erro": str(erro)
        }), 500



from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_DRIVE_FILE = "/etc/secrets/google-drive.json"
FOTOS_FOLDER_ID = "1qiESmRhW96oMKFhPsR0YNvjbtARIHMZb"
VIDEOS_FOLDER_ID = "1QQZz03GPHDzY9iIMZZ1Pnc67wdKgFA-6"

def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_DRIVE_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print("ERRO DRIVE:", e)
        return None

def listar_drive(folder_id):
    service = get_drive_service()
    if not service:
        return []
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id,name,mimeType)",
            pageSize=200
        ).execute()
        return results.get("files", [])
    except Exception as e:
        print("ERRO LISTAR DRIVE:", e)
        return []


@app.route("/fotos")
def fotos_page():
    if not usuario_logado():
        return redirect(url_for("login_page"))
    return render_template("fotos.html")

@app.route("/videos")
def videos_page():
    if not usuario_logado():
        return redirect(url_for("login_page"))
    return render_template("videos.html")

@app.route("/api/imagem/<file_id>")
def api_imagem(file_id):
    return redirect(f"https://drive.google.com/thumbnail?id={file_id}&sz=w2000")

@app.route("/api/video/<file_id>")
def api_video(file_id):
    return redirect(f"https://drive.google.com/file/d/{file_id}/preview")


@app.route("/api/fotos")
def api_fotos():
    return jsonify(listar_drive(FOTOS_FOLDER_ID))

@app.route("/api/videos")
def api_videos():
    return jsonify(listar_drive(VIDEOS_FOLDER_ID))

init_db()

try:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email TEXT;")
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS senha TEXT;")
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS codigo TEXT;")
except Exception as erro:
    print("AVISO AO GARANTIR COLUNAS DE CADASTRO:", erro)

if __name__ == "__main__":
    app.run(debug=True)
