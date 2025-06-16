

import discord
from discord.ext import commands, tasks
import datetime
import csv
import os
from collections import defaultdict

import os
TOKEN = os.environ['TOKEN']

CSV_FILE = 'registro.csv'
CANAL_FICHAJE_ID = 1383986991280160828  # ID del canal donde están los botones
CANAL_RESUMEN_ID = 1384006193164587099  # ID del canal donde se enviará el resumen semanal

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

fichajes = {}

# --- VISTA DE BOTONES ---
class FicharView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrada a servicio", style=discord.ButtonStyle.green)
    async def entrada(self, interaction: discord.Interaction, button: discord.ui.Button):
        usuario = interaction.user.name
        fichajes[usuario] = datetime.datetime.now()
        await interaction.response.send_message(f"✅ {usuario}, hora de entrada registrada: {fichajes[usuario].strftime('%H:%M:%S')}", ephemeral=True)

    @discord.ui.button(label="Salida de servicio", style=discord.ButtonStyle.red)
    async def salida(self, interaction: discord.Interaction, button: discord.ui.Button):
        usuario = interaction.user.name
        salida = datetime.datetime.now()
        entrada = fichajes.get(usuario)

        if entrada:
            duracion = salida - entrada
            segundos = int(duracion.total_seconds())
            fecha = entrada.date().isoformat()

            if not os.path.exists(CSV_FILE):
                with open(CSV_FILE, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Usuario", "Fecha", "Entrada", "Salida", "Tiempo_Segundos"])

            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([usuario, fecha, entrada.strftime('%H:%M:%S'), salida.strftime('%H:%M:%S'), segundos])

            del fichajes[usuario]
            await interaction.response.send_message(
                f"⏹️ {usuario}, hora de salida registrada: {salida.strftime('%H:%M:%S')}.\n🕒 Tiempo trabajado: {str(duracion)}",
                ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No has registrado una hora de entrada.", ephemeral=True)

# --- EVENTO AL INICIAR BOT ---
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    canal = bot.get_channel(CANAL_FICHAJE_ID)
    if canal:
        await canal.send("📋 **Fichaje de servicio**", view=FicharView())
    resumen_semanal_auto.start()

# --- COMANDO MANUAL: RESUMEN SEMANAL ---
@bot.command(name="resumen")
async def resumen(ctx):
    await generar_resumen(ctx.send)

# --- FUNCIÓN PARA GENERAR RESUMEN Y GUARDAR ---
async def generar_resumen(send_func):
    if not os.path.exists(CSV_FILE):
        await send_func("No hay registros aún.")
        return

    trabajo_por_usuario = defaultdict(lambda: defaultdict(int))

    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            usuario = row["Usuario"]
            fecha = row["Fecha"]
            segundos = int(row["Tiempo_Segundos"])
            trabajo_por_usuario[usuario][fecha] += segundos

    if not trabajo_por_usuario:
        await send_func("No hay datos suficientes.")
        return

    resumen_msg = "**📋 Informe semanal de trabajo:**\n\n"

    for usuario, dias in trabajo_por_usuario.items():
        total_segundos = sum(dias.values())
        dias_trabajados = len(dias)

        horas_totales, resto = divmod(total_segundos, 3600)
        minutos_totales, segundos_totales = divmod(resto, 60)

        resumen_msg += f"👤 **{usuario}**\n"
        resumen_msg += f"• Días trabajados: {dias_trabajados}\n"
        resumen_msg += f"• Total: {horas_totales}h {minutos_totales}m {segundos_totales}s\n"
        resumen_msg += "• Detalle diario:\n"
        for fecha, segundos in sorted(dias.items()):
            h, r = divmod(segundos, 3600)
            m, s = divmod(r, 60)
            resumen_msg += f"   └─ {fecha}: {h}h {m}m {s}s\n"
        resumen_msg += "\n"

    semana_actual = datetime.date.today().isocalendar().week
    resumen_filename = f"resumen_semana_{semana_actual}.txt"
    with open(resumen_filename, "w", encoding="utf-8") as resumen_file:
        resumen_file.write(resumen_msg)

    await send_func("📁 Resumen semanal generado:", file=discord.File(resumen_filename))

    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Usuario", "Fecha", "Entrada", "Salida", "Tiempo_Segundos"])

# --- TAREA AUTOMÁTICA CADA LUNES ---
@tasks.loop(hours=24)
async def resumen_semanal_auto():
    if datetime.datetime.today().weekday() != 0:
        return  # Solo lunes

    canal = bot.get_channel(CANAL_RESUMEN_ID)
    if canal:
        await generar_resumen(canal.send)

# --- EJECUTAR BOT ---
bot.run(TOKEN)






