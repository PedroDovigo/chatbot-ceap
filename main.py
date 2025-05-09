from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class Pergunta(BaseModel):
    pergunta: str

# Configuração da API do Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
chat = model.start_chat()
respostas_cache = {}

# Função que carrega os dados da planilha online via Google Sheets
def carregar_dados_google_sheet():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    cred_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    cred_dict = json.loads(cred_json)
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
    client = gspread.authorize(credentials)
    planilha = client.open("faq")
    aba = planilha.sheet1
    registros = aba.get_all_records()
    return pd.DataFrame(registros)

# Função que monta o prompt
def montar_prompt(pergunta_usuario, df):
    dados_texto = df.head(10).to_string(index=False)
    return f"""
Você é um analista de dados. Com base nas primeiras linhas da planilha abaixo, responda à pergunta:

{dados_texto}

Pergunta: {pergunta_usuario}
"""

# Endpoint de resposta
@app.post("/chat")
def responder(p: Pergunta):
    if p.pergunta in respostas_cache:
        return {"resposta": respostas_cache[p.pergunta]}
    df = carregar_dados_google_sheet()
    prompt = montar_prompt(p.pergunta, df)
    resposta = chat.send_message(prompt).text
    respostas_cache[p.pergunta] = resposta
    return {"resposta": resposta}
