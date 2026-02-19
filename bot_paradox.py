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
cofres_liberacao = {} 

@app.route('/')
def home(): return "Bot Online!"

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    if data and 'nome' in data:
        status = data['status']
        if "ROUBANDO" in status:
            cofres_liberacao[data['nome']] = "ROUBANDO..."
        elif status.count(':') == 2: # Formato HH:MM:SS
            h, m, s = map(int, status.split(':'))
            segundos_faltando = h * 3600 + m * 60 + s
            cofres_liberacao[data['nome']] = time.time() + segundos_faltando
        else:
            cofres_liberacao[data['nome']] = "LIVRE"
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
                if isinstance(val, float):
                    restante = int(val - agora)
                    if restante > 0:
                        m, s = divmod(restante, 60)
                        h, m = divmod(m, 60)
                        status_str = f"🔴 `释放: {h:02d}:{m:02d}:{s:02d}`"
                    else:
                        status_str = "🟢 **LIVRE**"
                elif val == "ROUBANDO...":
                    status_str = "🟡 **ROUBANDO...**"
                else:
                    status_str = "🟢 **LIVRE**"
                
                descricao += f"**{nome}**: {status_str}\n"
            
            embed.description = descricao
            embed.set_footer(text="Atualizando em tempo real • v0.4")

            try:
                # Tenta encontrar a última mensagem do bot no canal para editar
                if msg_painel is None:
                    async for message in canal.history(limit=10):
                        if message.author == bot.user:
                            msg_painel = message
                            break
                
                if msg_painel:
                    await msg_painel.edit(embed=embed)
                else:
                    # Se não achou nenhuma, limpa o canal e envia uma nova
                    await canal.purge(limit=5, check=lambda m: m.author == bot.user)
                    msg_painel = await canal.send(embed=embed)
            except Exception as e:
                print(f"Erro ao atualizar: {e}")
                msg_painel = None # Reseta para tentar achar/criar na próxima volta
        
        await asyncio.sleep(1) # Atualiza o cronômetro a cada 1 segundo

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

@bot.event
async def on_ready():
    print(f'✅ Bot conectado: {bot.user}')
    bot.loop.create_task(atualizar_painel())

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
