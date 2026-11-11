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
        "<code>https://t.me/nft/Название-123</code>"
    )

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
            InlineKeyboardButton(text="⭐ Stars", callback_data="cur:stars"),
            InlineKeyboardButton(text="💎 Gram", callback_data="cur:gram"),
            InlineKeyboardButton(text="💎 TON", callback_data="cur:ton"),
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
        currency_text = "⭐"
    elif currency == "gram":
        currency_text = "Gram"
    else:
        currency_text = "TON"

    text = (
        f"{link}\n\n"
        f"Предлагаю <b>{price} {currency_text}</b> за этот подарок"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть подарок", url=link)],
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept:{callback.from_user.id}:{price}:{currency}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline:{callback.from_user.id}")
        ]
    ])

    await callback.message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)
    await callback.answer()

@dp.callback_query(F.data.startswith("accept:"))
async def accept_offer(callback: CallbackQuery):
    parts = callback.data.split(":")
    seller_id = int(parts[1])
    price = parts[2]
    currency = parts[3]

    await callback.answer("Вы приняли предложение")
    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        await bot.send_message(
            seller_id,
            f"✅ Кто-то принял твоё предложение за <b>{price} {currency}</b>\n"
            f"Пользователь: @{callback.from_user.username or callback.from_user.full_name}"
        )
    except:
        pass

@dp.callback_query(F.data.startswith("decline:"))
async def decline_offer(callback: CallbackQuery):
    parts = callback.data.split(":")
    seller_id = int(parts[1])

    await callback.answer("Вы отклонили предложение")
    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        await bot.send_message(
            seller_id,
            f"❌ Кто-то отклонил твоё предложение.\n"
            f"Пользователь: @{callback.from_user.username or callback.from_user.full_name}"
        )
    except:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
