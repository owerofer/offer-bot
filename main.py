import re
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

INFO_PATTERN = re.compile(
    r"^/info\s+(https?://\S+)\s+(\d+)(?:\s+(gram))?(?:\s+(ru|en|zh))?$",
    re.IGNORECASE
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Бот готов!\n\n"
        "Пиши:\n"
        "<code>/info ссылка цена</code>\n"
        "<code>/info ссылка цена gram</code>\n\n"
        "Пример:\n"
        "<code>/info https://t.me/nft/GiftName 1000</code>"
    )

@dp.message(F.text.regexp(INFO_PATTERN))
async def process_info(message: types.Message):
    match = INFO_PATTERN.match(message.text.strip())
    if not match:
        return

    link = match.group(1)
    price = match.group(2)
    is_gram = bool(match.group(3))

    try:
        await message.delete()
    except:
        pass

    price_text = f"<b>{price} Gram</b>" if is_gram else f"{price} ⭐"

    text = (
        f"🎁 <b>Новый оффер</b>\n\n"
        f"🔗 {link}\n"
        f"💰 {price_text}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть", url=link)]
    ])

    await message.answer(text, reply_markup=kb)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
