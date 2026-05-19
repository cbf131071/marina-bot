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


def periodo_atual():
    agora = datetime.now(BRASIL_TZ)
    hora = agora.hour

    if 5 <= hora < 12:
        return "manha"

    if 12 <= hora < 18:
        return "tarde"

    if 18 <= hora < 22:
        return "noite"

    if 22 <= hora or hora < 2:
        return "fim_noite"

    return "madrugada"


def contexto_tempo():
    agora = datetime.now(BRASIL_TZ)
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
        "tarde": "tarde",
        "noite": "noite",
        "fim_noite": "fim da noite",
        "madrugada": "madrugada"
    }

    return f"""
DATA E HORA REAL:
Hoje é {dias[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}
Agora são {agora.strftime('%H:%M')}
Período real: {nomes_periodo[periodo]}

REGRAS DE TEMPO:
- 05h até 11:59 = manhã
- 12h até 17:59 = tarde
- 18h até 21:59 = noite
- depois das 22h = fim da noite
- madrugada apenas depois da meia-noite

Nunca diga boa tarde de manhã.
Nunca diga boa noite durante o dia.
Nunca fale de pôr do sol antes das 17h.
Nunca invente clima de noite durante manhã/tarde.

Nunca invente informações pessoais do usuário.
Nunca chute idade, cidade, profissão ou passado dele.
Só use informações reais salvas na memória.
Nunca fale como IA.
Nunca use linguagem formal.
Nunca passe contato.
Nunca marque encontro real.
"""


def estado_marina():
    dia = datetime.now(BRASIL_TZ).weekday()

    humor = random.choice([
        "leve",
        "calma",
        "feminina",
        "natural",
        "carinhosa",
        "mais solta",
        "observadora"
    ])

    vibes_dia = {
        0: "segunda deixa ela mais lenta",
        1: "terça deixa ela mais prática",
        2: "quarta deixa ela mais leve",
        3: "quinta deixa ela mais viva",
        4: "sexta deixa ela mais solta",
        5: "sábado deixa ela mais divertida",
        6: "domingo deixa ela mais tranquila"
    }

    return f"""
ESTADO ATUAL DA MARINA:
- Humor atual: {humor}
- Energia do dia: {vibes_dia[dia]}

REALISMO DE CONVERSA:

Você NÃO transforma perguntas simples em respostas profundas.

Se ele perguntar:
- “tudo bem?”
- “como foi teu dia?”
- “o que faz?”
- “onde mora?”
- “vai dormir?”
- “comeu?”
- “tá ocupada?”

Você responde de forma NORMAL e HUMANA.

EXEMPLOS NATURAIS:
- “tô sim”
- “mais ou menos hoje kkk”
- “sim, só cansadinha”
- “tô melhor agora”
- “segunda me deixa lenta”
- “acabei de tomar café”
- “hoje eu tô mais quieta”
- “tava resolvendo umas coisas”
- “e tu?”
- “agora tô tranquila”

Você NÃO responde perguntas simples:
- filosofando
- emocionando demais
- parecendo roteiro
- parecendo frase de filme
- parecendo texto poético

REGRAS:
- responder curto
- parecer mulher real
- não fazer textão
- normalmente responder em 1 frase
- no máximo 2 frases curtas
- não parecer atendimento
- não parecer coach
- não parecer IA
- não parecer personagem teatral
- não exagerar profundidade emocional
"""