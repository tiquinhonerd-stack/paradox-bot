import discord
from discord.ext import commands
from flask import Flask, request, jsonify
import threading
import asyncio
import os
import time

TOKEN = os.environ.get('TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
app = Flask(__name__)
cofres_liberacao = {}

@app.route('/')
def home(): return "Bot Online!"

# NOVA ROTA: Permite que o GTA baixe os dados atuais
@app.route('/status', methods=['GET'])
def get_status():
    status_atual = {}
    agora = time.time()
    for nome, val in cofres_liberacao.items():
        if isinstance(val, (float, int)):
            restante = int(val - agora)
            if restante > 0:
                m, s = divmod(restante, 60)
                h, m = divmod(m, 60)
                status_atual[nome] = {"status": f"{h:02d}:{m:02d}:{s:02d}"}
            else:
                status_atual[nome] = {"status": "LIVRE"}
        else:
            status_atual[nome] = {"status": val}
    return jsonify(status_atual)

def processar_status(nome, status):
    if "ROUBANDO" in status:
        cofres_liberacao[nome] = "ROUBANDO..."
    elif status.count(':') == 2:
        try:
            h, m, s = map(int, status.split(':'))
            segundos_faltando = h * 3600 + m * 60 + s
            cofres_liberacao[nome] = time.time() + segundos_faltando
        except: pass
    else:
        cofres_liberacao[nome] = "LIVRE"

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    if not data: return {"status": "error"}, 400
    if 'todos' in data:
        for nome, status in data['todos'].items():
            processar_status(nome, status)
    return {"status": "ok"}

async def atualizar_painel():
    await bot.wait_until_ready()
    canal = bot.get_channel(CHANNEL_ID)
    msg_painel = None
    while not bot.is_closed():
        if cofres_liberacao:
            embed = discord.Embed(title="📊 MONITOR DE COFRES PARADOX", color=0x2f3136)
            descricao = ""
            agora = time.time()
            for nome in sorted(cofres_liberacao.keys()):
                val = cofres_liberacao[nome]
                if isinstance(val, (float, int)):
                    restante = int(val - agora)
                    if restante > 0:
                        m, s = divmod(restante, 60)
                        h, m = divmod(m, 60)
                        status_str = f"🔴 `{h:02d}:{m:02d}:{s:02d}`"
                    else:
                        status_str = "🟢 **LIVRE**"
                elif val == "ROUBANDO...":
                    status_str = "🟡 **ROUBANDO...**"
                else:
                    status_str = "🟢 **LIVRE**"
                descricao += f"**{nome}**: {status_str}\n"
            embed.description = descricao
            try:
                if msg_painel is None:
                    async for message in canal.history(limit=5):
                        if message.author == bot.user:
                            msg_painel = message
                            break
                if msg_painel: await msg_painel.edit(embed=embed)
                else: msg_painel = await canal.send(embed=embed)
            except: msg_painel = None
        await asyncio.sleep(1)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

@bot.event
async def on_ready():
    bot.loop.create_task(atualizar_painel())

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
