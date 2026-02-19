"""
Discord bot - runs as a separate process (not inside FastAPI).

Start: python -m app.discord_bot

Features:
- /registrar slash command: links Discord account to student record via onboarding token
- on_member_join: DMs instructions to new members who don't have product roles
"""
import logging
import sys
from datetime import datetime, timezone

import discord
from discord import app_commands
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.user import User, LifecycleStatus
from app.models.event import Event, EventStatus

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.members = True  # Required for on_member_join


class AutograderBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=int(settings.discord_guild_id))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info("Slash commands synced to guild %s", settings.discord_guild_id)

    async def on_ready(self):
        logger.info("Bot ready: %s (id=%s)", self.user, self.user.id)


bot = AutograderBot()


@bot.tree.command(name="registrar", description="Registre sua conta no autograder com o código enviado por WhatsApp")
@app_commands.describe(codigo="Código de 8 caracteres enviado via WhatsApp")
async def registrar(interaction: discord.Interaction, codigo: str):
    """Link a Discord account to a student record via onboarding token."""
    # Restrict to registration channel if configured
    if settings.discord_registration_channel_id:
        if str(interaction.channel_id) != settings.discord_registration_channel_id:
            await interaction.response.send_message(
                "Use este comando no canal #registro.",
                ephemeral=True,
            )
            return

    discord_id = str(interaction.user.id)

    db: Session = SessionLocal()
    try:
        # Check if already registered
        existing = db.query(User).filter(User.discord_id == discord_id).first()
        if existing:
            await interaction.response.send_message(
                "Você já está registrado!",
                ephemeral=True,
            )
            return

        # Find user by token
        token = codigo.strip().upper()
        user = db.query(User).filter(User.onboarding_token == token).first()

        if not user:
            await interaction.response.send_message(
                "Código inválido. Verifique o WhatsApp com as instruções.",
                ephemeral=True,
            )
            return

        if user.onboarding_token_expires_at and user.onboarding_token_expires_at < datetime.now(timezone.utc):
            await interaction.response.send_message(
                "Código expirado. Solicite um novo no WhatsApp.",
                ephemeral=True,
            )
            return

        # Link Discord account
        user.discord_id = discord_id
        user.onboarding_token = None
        user.onboarding_token_expires_at = None

        # Log the registration event
        reg_event = Event(
            type="discord.registration_completed",
            target_id=user.id,
            payload={"discord_id": discord_id},
            status=EventStatus.PROCESSED,
        )
        db.add(reg_event)
        db.flush()

        # Trigger lifecycle transition to active
        from app.services.lifecycle import transition
        transition(
            db,
            user,
            trigger="discord_registered",
        )

        db.commit()

        await interaction.response.send_message(
            "Registrado! Acesso liberado. Bem-vindo(a) ao curso!",
            ephemeral=True,
        )

    except Exception as e:
        db.rollback()
        logger.error("Error in /registrar command: %s", e)
        await interaction.response.send_message(
            "Ocorreu um erro ao processar seu registro. Tente novamente em alguns instantes.",
            ephemeral=True,
        )
    finally:
        db.close()


@bot.event
async def on_member_join(member: discord.Member):
    """Send a DM to new members who don't have product roles."""
    if str(member.guild.id) != settings.discord_guild_id:
        return

    # Check if member has any roles beyond @everyone
    if len(member.roles) > 1:
        return

    try:
        await member.send(
            f"Olá {member.display_name}! Bem-vindo(a) ao servidor.\n\n"
            "Para liberar o acesso ao conteúdo, você precisa registrar sua conta.\n"
            "1. Acesse o canal #registro\n"
            "2. Use o comando `/registrar codigo:SEU_CODIGO`\n"
            "   (o código foi enviado via WhatsApp quando você fez a compra)\n\n"
            "Se não recebeu o código ou ele expirou, entre em contato com o suporte."
        )
        logger.info("Sent welcome DM to new member %s", member.id)
    except discord.Forbidden:
        logger.warning("Could not send DM to member %s (DMs disabled)", member.id)


def main():
    if not settings.discord_bot_token:
        logger.error("DISCORD_BOT_TOKEN is not set. Bot cannot start.")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Discord bot...")
    bot.run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
