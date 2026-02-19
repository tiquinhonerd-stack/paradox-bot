import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import os

# O Bot vai ler esses valores das configurações do Render
TOKEN = os.environ.get('TOKEN')
CHANNEL_ID_STR = os.environ.get('CHANNEL_ID')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
app = Flask(__name__)
msg_painel = None
cofres_status = {}

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    nome = data.get('nome')
    status = data.get('status')
    if nome:
        cofres_status[nome] = status
    return {"status": "ok"}

async def atualizar_painel():
    await bot.wait_until_ready()
    try:
        canal = bot.get_channel(int(CHANNEL_ID_STR))
    except:
        print("ERRO: CHANNEL_ID inválido nas configurações do Render!")
        return

    global msg_painel
    while not bot.is_closed():
        if cofres_status:
            embed = discord.Embed(title="📊 MONITOR DE COFRES PARADOX", color=0x00FF00)
            descricao = ""
            for nome in sorted(cofres_status.keys()):
                status = cofres_status[nome]
                emoji = "🟢" if "LIVRE" in status else "🔴" if ":" in status else "🟡"
                descricao += f"{emoji} **{nome}**: {status}\n"
            
            embed.description = descricao
            embed.set_footer(text="Atualizado em tempo real via Cloud")
            
            try:
                if msg_painel is None:
                    msg_painel = await canal.send(embed=embed)
                else:
                    await msg_painel.edit(embed=embed)
            except Exception as e:
                print(f"Erro ao editar/enviar: {e}")
        await asyncio.sleep(10)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user}')
    bot.loop.create_task(atualizar_painel())

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)
