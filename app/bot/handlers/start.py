from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot import texts

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(texts.WELCOME, parse_mode="HTML")


@router.message(Command("yordam"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP, parse_mode="HTML")
