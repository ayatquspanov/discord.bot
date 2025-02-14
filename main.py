import discord
from discord.ext import commands
from discord import Intents, PermissionOverwrite, ButtonStyle
from discord.ui import View, Button, Select
import datetime
import os
import asyncio

intents = Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_ROLE_NAME = "・ Control"
TICKET_LOG_CHANNEL_ID = 1338527420503822439  # Лог сақталатын каналдың ID-сі
TICKET_BANNER_URL = "https://cdn.discordapp.com/attachments/1048316616334651484/1339791334726438933/IMG_7125.png"

@bot.event
async def on_ready():
    print(f"✅ Бот іске қосылды: {bot.user}")

@bot.command()
async def setup_ticket(ctx):
    category = discord.utils.get(ctx.guild.categories, name="Поддержка")
    if not category:
        await ctx.send("❌ 'Поддержка' категориясы табылмады!")
        return

    embed = discord.Embed(color=discord.Color.blue())
    embed.set_image(url=TICKET_BANNER_URL)

    view = TicketView()
    await ctx.send(embed=embed, view=view)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Тикет ашу", style=ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name="Поддержка")
        if not category:
            await interaction.response.send_message("❌ 'Поддержка' категориясы табылмады!", ephemeral=True)
            return

        channel_name = f"ticket-{user.name}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"❌ Сіздің тикетіңіз ашылған: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: PermissionOverwrite(view_channel=False),
            user: PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }

        admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role:
            overwrites[admin_role] = PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        embed = discord.Embed(color=discord.Color.green())
        embed.set_image(url=TICKET_BANNER_URL)

        view = AdminControlView()
        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(f"✅ Сіздің тикетіңіз ашылды: {channel.mention}", ephemeral=True)

class AdminControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Адам қосу", style=ButtonStyle.blurple, custom_id="add_user")
    async def add_user(self, interaction: discord.Interaction, button: Button):
        if not any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles):
            await interaction.response.send_message("❌ Тикетке адам қосуды тек администраторлар жасай алады.", ephemeral=True)
            return

        view = AddUserDropdown(interaction.channel)
        await interaction.response.send_message("👥 Қосылатын адамды таңдаңыз:", view=view, ephemeral=True)

    @discord.ui.button(label="🔒 Тикетті жабу", style=ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if not any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles):
            await interaction.response.send_message("❌ Тикетті тек админ жаба алады.", ephemeral=True)
            return

        channel = interaction.channel
        await interaction.response.send_message("🔴 Тикет 5 секундтан кейін жабылады...", ephemeral=True)

        messages = []
        async for message in channel.history(limit=100):
            messages.append(f"<p><strong>{message.author.name}:</strong> {message.content}</p>")

        messages.reverse()

        html_content = f"""
        <html>
        <head>
            <title>{channel.name} - Ticket Log</title>
        </head>
        <body>
            <h2>Тикет: {channel.name}</h2>
            <h3>Жабылған уақыт: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h3>
            {''.join(messages)}
        </body>
        </html>
        """

        file_path = f"{channel.name}.html"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(html_content)

        log_channel = discord.utils.get(interaction.guild.text_channels, id=TICKET_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(content="📂 Тикет логын жүктеу:", file=discord.File(file_path))

        os.remove(file_path)

        await asyncio.sleep(5)
        await channel.delete()

class AddUserDropdown(View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=30)
        self.channel = channel

        options = [
            discord.SelectOption(label=member.name, value=str(member.id))
            for member in channel.guild.members if not member.bot
        ]
        
        if not options:
            options = [discord.SelectOption(label="Пайдаланушылар табылмады", value="none", default=True)]

        self.select_menu = Select(placeholder="👥 Тикетке адам қосу...", options=options, custom_id="add_user_dropdown")
        self.select_menu.callback = self.on_select
        self.add_item(self.select_menu)

    async def on_select(self, interaction: discord.Interaction):
        member_id = self.select_menu.values[0]

        if member_id == "none":
            await interaction.response.send_message("❌ Қате: Қосатын пайдаланушылар табылмады.", ephemeral=True)
            return

        member = interaction.guild.get_member(int(member_id))
        if member:
            await self.channel.set_permissions(member, view_channel=True, send_messages=True, attach_files=True)
            await interaction.response.send_message(f"✅ {member.mention} тикетке қосылды!", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Қате: Пайдаланушы табылмады.", ephemeral=True)

### Токен осында жаз
bot.run("MTA3MjkwMzMzODkwNTA0MzAyNA.Gmz43Z.PSpdRiCwKY_82HWdUeWkjbe78llzMBKiGGDdF4")
