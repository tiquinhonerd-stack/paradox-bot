import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import os
import time

TOKEN = os.environ.get('TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
app = Flask(__name__)
msg_painel_id = None
cofres_liberacao = {} # Armazena o timestamp de quando vai liberar

@app.route('/')
def home(): return "Bot Online!"

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    if data and 'nome' in data:
        # Recebe o tempo que falta em segundos e soma com o tempo atual do servidor
        if ":" in data['status'] or "ROUBANDO" in data['status']:
            cofres_liberacao[data['nome']] = data['status']
        else:
            cofres_liberacao[data['nome']] = "LIVRE"
            
        # Se for tempo (formato HH:MM:SS), calculamos o momento exato da liberação
        if data['status'].count(':') == 2:
            h, m, s = map(int, data['status'].split(':'))
            segundos_faltando = h * 3600 + m * 60 + s
            cofres_liberacao[data['nome']] = time.time() + segundos_faltando
            
    return {"status": "ok"}

async def atualizar_painel():
    await bot.wait_until_ready()
    canal = bot.get_channel(CHANNEL_ID)
    global msg_painel_id

    while not bot.is_closed():
        if cofres_liberacao:
            embed = discord.Embed(title="📊 MONITOR DE COFRES PARADOX", color=0x00FF00)
            descricao = ""
            agora = time.time()
            
            for nome in sorted(cofres_liberacao.keys()):
                val = cofres_liberacao[nome]
                
                if isinstance(val, float): # Se for um timestamp de liberação
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
                msg = None
                if msg_painel_id:
                    try: msg = await canal.fetch_message(msg_painel_id)
                    except: msg = None
                
                if msg: await msg.edit(embed=embed)
                else:
                    await canal.purge(limit=2)
                    nova_msg = await canal.send(embed=embed)
                    msg_painel_id = nova_msg.id
            except: pass
        
        await asyncio.sleep(1) # ATUALIZA A CADA 1 SEGUNDO

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
