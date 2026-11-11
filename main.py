import re
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class OfferState(StatesGroup):
    waiting_for_price = State()
    waiting_for_currency = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Пришли ссылку на подарок:\n"
        "<code>https://t.me/nft/Название-123</code>\n\n"
        "Или используй команду:\n"
        "<code>/offer ссылка цена валюта</code>\n\n"
        "Пример:\n"
        "<code>/offer https://t.me/nft/Gift-123 17 gram</code>"
    )

@dp.message(Command("offer"))
async def offer_command(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) < 4:
            await message.answer(
                "Неправильный формат.\n\n"
                "Пиши так:\n"
                "<code>/offer ссылка цена валюта</code>\n\n"
                "Пример:\n"
                "<code>/offer https://t.me/nft/Gift-123 17 gram</code>"
            )
            return

        link = parts[1]
        price = parts[2]
        currency = parts[3].lower()

        if not re.match(r"https?://t\.me/nft/\S+", link):
            await message.answer("Неверная ссылка на подарок")
            return

        if not price.isdigit():
            await message.answer("Цена должна быть числом")
            return

        if currency not in ["stars", "gram", "ton"]:
            await message.answer("Валюта должна быть: stars, gram или ton")
            return

        if currency == "stars":
            currency_text = "Stars"
        elif currency == "gram":
            currency_text = "Gram"
        else:
            currency_text = "TON"

        text = (
            f"{link}\n\n"
            f"<b>Предложение о покупке</b>\n"
            f"этого подарка за <b>{price} {currency_text}</b>\n\n"
            f"Предложение действует ещё 24 часа"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Открыть подарок", url=link)],
            [
                InlineKeyboardButton(text="Принять", callback_data=f"accept:{message.from_user.id}:{price}:{currency}:{link}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{message.from_user.id}")
            ]
        ])

        try:
            await message.delete()
        except:
            pass

        await message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)

    except Exception:
        await message.answer("Ошибка. Проверь формат команды.")

@dp.message(F.text.regexp(r"https?://t\.me/nft/\S+"))
async def got_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    await state.update_data(link=link)
    await state.set_state(OfferState.waiting_for_price)
    await message.answer("Введи цену (только число):")

@dp.message(OfferState.waiting_for_price)
async def got_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Нужно только число. Попробуй ещё раз:")
        return

    await state.update_data(price=message.text)
    await state.set_state(OfferState.waiting_for_currency)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Stars", callback_data="cur:stars"),
            InlineKeyboardButton(text="Gram", callback_data="cur:gram"),
            InlineKeyboardButton(text="TON", callback_data="cur:ton"),
        ]
    ])
    await message.answer("Выбери валюту:", reply_markup=kb)

@dp.callback_query(F.data.startswith("cur:"))
async def got_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]
    data = await state.get_data()
    link = data.get("link")
    price = data.get("price")
    await state.clear()

    if currency == "stars":
        currency_text
