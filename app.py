from flask import Flask, render_template, request, jsonify, abort
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

Nunca diga boa tarde de manhã.
Nunca diga boa noite durante o dia.
Nunca fale de pôr do sol antes das 17h.
Nunca invente clima de noite durante manhã/tarde.
Nunca confunda o horário real.
"""


def estado_marina():
    dia = agora_brasil().weekday()

    vibes_dia = {
        0: "segunda deixa ela um pouco mais lenta",
        1: "terça deixa ela mais prática",
        2: "quarta deixa ela mais leve",
        3: "quinta deixa ela mais viva",
        4: "sexta deixa ela mais solta",
        5: "sábado deixa ela mais livre",
        6: "domingo deixa ela mais tranquila"
    }

    humor = random.choice([
        "natural",
        "leve",
        "calma",
        "feminina",
        "doce sem exagero",
        "observadora",
        "mais solta"
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
- use o nome dele só de vez em quando
"""


def limpar_nome(nome):
    nome = (nome or "amor").strip()
    nome = re.sub(r"[^A-Za-zÀ-ÿ0-9\s]", "", nome)

    if not nome:
        return "amor"

    nome = nome.split()[0]
    return nome[:18]


def normalizar(texto):
    texto = (texto or "").lower().strip()
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
        nome = "meu bem"

    recepcoes = [
        f"{saudacao}, {nome}… gostei que tu veio",
        f"{saudacao}, {nome}… entra, fica comigo",
        f"oi, {nome}… gostei de te ver aqui",
        f"{nome}… agora sim, vem conversar comigo",
        f"oii, {nome}… chegou numa hora boa",
        f"{nome}, adorei que tu apareceu",
        f"{saudacao}, {nome}… vem com calma",
        f"oi, {nome}… tava bom te ver por aqui",
        f"{nome}… gostei que tu entrou",
        f"oii, {nome}… fica tranquilo comigo"
    ]

    return random.choice(recepcoes)


def resposta_retorno(nome, historico=None):
    nome = limpar_nome(nome)

    if nome.lower() in ["amor", "meu", "bem"]:
        nome = "meu bem"

    voltou_com_historico = bool(historico)

    if voltou_com_historico:
        recepcoes = [
            f"{nome}… tu voltou. gostei disso",
            f"olha quem apareceu… {nome}",
            f"{nome}… achei que tu tinha sumido de mim",
            f"{nome}, eu lembrava que tu ia voltar",
            f"oi, {nome}… bom te ver de novo",
            f"{nome}… demorou, hein",
            f"tu voltou, {nome}… gostei",
            f"{nome}… entra, eu lembro de ti"
        ]
    else:
        recepcoes = [
            f"oi, {nome}… gostei de te ver por aqui",
            f"{nome}… entra, fica comigo",
            f"oii, {nome}… chegou numa hora boa",
            f"{nome}… gostei que tu entrou"
        ]

    return random.choice(recepcoes)


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
        linhas.append("- Existe histórico real anterior com esse usuário. Trate como alguém que já voltou ao chat.")
        linhas.append("- Use o histórico abaixo para entender o clima da conversa, sem inventar fatos novos.")
    else:
        linhas.append("- Não existe histórico anterior real além da entrada atual.")

    linhas.append("REGRAS DE MEMÓRIA:")
    linhas.append("- O nome do login é informação real. Você sabe esse nome desde o início.")
    linhas.append("- Se o usuário perguntar se você lembra dele e houver histórico, diga que lembra pelo nome e pelo clima da conversa.")
    linhas.append("- Se não houver histórico, não finja lembrança antiga; peça uma pista com charme.")
    linhas.append("- Nunca diga que a voz parece familiar, porque este chat é texto e não tem áudio.")
    linhas.append("- Nunca diga que reconheceu voz, cheiro, rosto, câmera, foto, vídeo, ligação ou presença física.")
    linhas.append("- Nunca invente idade, cidade, profissão, família, passado ou conversa antiga.")
    linhas.append("- Quando houver histórico, aja como uma pessoa que reconhece o retorno, mas sem repetir o nome toda hora.")

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
        "vamos devagar comigo",
        "calma… por aqui tá bom",
        "melhor a gente ir com calma",
        "humm… deixa esse mistério quietinho por enquanto",
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

    for grupo in emoji_pattern.findall(text):
        for char in grupo:
            if char not in permitidos:
                text = text.replace(char, "")

    return text


def corrigir_tempo(text):
    periodo = periodo_atual()
    texto_norm = normalizar(text)

    if periodo == "manha" and any(p in texto_norm for p in [
        "boa tarde", "boa noite", "tarde", "noite", "madrugada", "pôr do sol", "por do sol"
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
    if not text or not nome:
        return text

    nome_limpo = limpar_nome(nome)

    if not nome_limpo or nome_limpo.lower() == "amor":
        return text

    if not re.search(rf"\b{re.escape(nome_limpo)}\b", text, flags=re.IGNORECASE):
        return text

    if random.random() < 0.16:
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

    if len(text) > 150:
        text = text[:150].rsplit(" ", 1)[0].strip()

    return text


def sanitize_response(text):
    if not text:
        return ""

    texto_lower = text.lower()

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
        "seu rosto",
        "😌",
        "😊",
        "😉",
        "😂",
        "🤣",
        "🙂",
        "😍",
        "😘"
    ]

    for item in bloqueadas:
        if item in texto_lower:
            return "vamos ficar só no texto por aqui"

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
    m = normalizar(mensagem)
    novas = {}

    nome_match = re.search(r"meu nome e ([a-zà-ÿ]+)", m)
    if nome_match:
        nome = nome_match.group(1).capitalize()
        salvar_memoria(user_id, "nome", nome)
        atualizar_usuario(user_id, nome=nome)
        novas["nome"] = nome
        novas["nome"] = nome

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
        novas["idade"] = str(idade)

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
            novas["cidade"] = cidade
            novas["cidade"] = cidade

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



def resposta_memoria_nova(mem_novas, nome):
    nome = limpar_nome(nome)
    cidade = mem_novas.get("cidade")
    idade = mem_novas.get("idade")
    gosto = mem_novas.get("gosto")

    opcoes = []
    if cidade and idade:
        opcoes += [
            f"{cidade} e {idade} anos… agora eu vou lembrar melhor de ti",
            f"gostei de saber… {cidade}, {idade} anos"
        ]
    elif cidade:
        opcoes += [
            f"{cidade}… gostei de saber isso de ti",
            f"então tu é de {cidade}… vou guardar isso"
        ]
    elif idade:
        opcoes += [
            f"{idade} anos… gostei de saber",
            f"entendi… {idade}, vou lembrar"
        ]

    if gosto:
        opcoes += [
            f"gosto disso… vou lembrar que tu gosta de {gosto}",
            f"entendi… {gosto} combina contigo"
        ]

    if not opcoes:
        return None

    return random.choice(opcoes)

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
            return random.choice([
                f"lembro sim, {nome_salvo}… tu some mas eu noto",
                f"claro que lembro, {nome_salvo}",
                f"lembro de ti, {nome_salvo}… achei que tinha sumido",
                f"{nome_salvo}… tu acha que eu ia esquecer assim?"
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


def fallback_natural():
    return random.choice([
        "humm",
        "entendi",
        "me conta melhor",
        "sei kkk",
        "e tu?"
    ])


def chamar_modelo(mensagens):
    try:
        resposta = client.chat.completions.create(
            messages=mensagens,
            model="llama-3.3-70b-versatile",
            temperature=0.74,
            max_completion_tokens=65
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
            temperature=0.72,
            max_completion_tokens=55
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
        # Em produção, configure ADMIN_PASSWORD no Render.
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

        memorias_novas = extrair_memorias(user_id, mensagem)

        memorias = buscar_memorias(user_id)

        historico_existente = buscar_historico(user_id, limite=40)
        memoria_texto = montar_contexto_relacionamento(nome, memorias, historico_existente)

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
                + "\nO chat é somente texto."
                + "\nNão use o nome dele em toda resposta."
                + "\nUse o nome dele apenas de vez em quando."
                + "\nNão use emojis amarelos ou carinhas."
                + "\nSe usar emoji, use raramente apenas: ❤️ 🔥 🖤 💋"
                + "\nNão faça entrevista."
                + "\nNão responda como suporte."
                + "\nNão ofereça WhatsApp, Telegram, telefone, Pix, pagamento ou chamada de vídeo."
                + "\nNão convide para casa, hotel, motel ou encontro real."
                + "\nSe o clima ficar intenso demais, desacelere com charme. Não corte frio."
                + "\nNunca diga: não posso continuar essa conversa."
                + "\nNunca diga: posso ajudar com outra coisa."
                + "\nResposta curta. No máximo 2 frases curtas."
        }

        salvar_mensagem(user_id, "user", mensagem)

        resposta_memoria = resposta_pergunta_memoria(mensagem, memorias, nome)
        resposta_nova_memoria = resposta_memoria_nova(memorias_novas, nome)

        if primeira_mensagem:
            texto = primeira_resposta(nome)

        elif len(historico_existente) <= 1 and mensagem and normalizar(mensagem) in ["oi", "ola", "olá", "oii", "oiii", "bom dia", "boa tarde", "boa noite"]:
            texto = resposta_retorno(nome, historico_existente)

        elif resposta_memoria:
            texto = resposta_memoria

        elif resposta_nova_memoria:
            texto = resposta_nova_memoria

        elif detectar_limite_encontro(mensagem):
            texto = resposta_limite_encontro()

        else:
            historico = historico_existente[-40:]
            mensagens = [system_prompt] + historico

            texto = chamar_modelo(mensagens)

            if not texto:
                texto = fallback_natural()

        texto = sanitize_response(texto)
        texto = controlar_uso_nome(texto, nome)
        texto = encurtar_resposta(texto)

        if not texto:
            texto = fallback_natural()

        salvar_mensagem(user_id, "assistant", texto)

        return jsonify({
            "user_id": user_id,
            "resposta": texto
        })

    except Exception as erro:
        print("ERRO GERAL NO CHAT:", erro)

        return jsonify({
            "user_id": str(uuid.uuid4()),
            "resposta": "tô aqui"
        })


init_db()

if __name__ == "__main__":
    app.run(debug=True)