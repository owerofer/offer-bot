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
# Сюда можно поставить свой Telegram ID, чтобы бот писал тебе уведомления
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class OfferState(StatesGroup):
    waiting_for_price = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! Я бот для создания офферов на подарки.\n\n"
        "Просто пришли мне ссылку на подарок:\n"
        "<code>https://t.me/nft/Название-123</code>"
    )

@dp.message(F.text.regexp(r"https?://t\.me/nft/\S+"))
async def got_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    await state.update_data(link=link)
    await state.set_state(OfferState.waiting_for_price)
    await message.answer("Введи цену в Stars или Gram целым числом (например 1500):")

@dp.message(OfferState.waiting_for_price)
async def got_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Нужно ввести только число. Попробуй ещё раз:")
        return

    price = message.text
    data = await state.get_data()
    link = data.get("link")
    await state.clear()

    # Красивая карточка
    text = (
        f"🎁 <b>Предложение о покупке</b>\n\n"
        f"🔗 Подарок: {link}\n"
        f"💰 Цена: <b>{price} ⭐</b>\n\n"
        f"Действительно 12 часов с момента отправки."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть подарок", url=link)],
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept:{message.from_user.id}:{price}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline:{message.from_user.id}")
        ],
        [InlineKeyboardButton(text="Написать продавцу", url=f"tg://user?id={message.from_user.id}")]
    ])

    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("accept:"))
async def accept_offer(callback: CallbackQuery):
    parts = callback.data.split(":")
    seller_id = int(parts[1])
    price = parts[2]

    await callback.answer("Вы приняли предложение")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Покупатель принял предложение!")

    # Уведомление продавцу
    try:
        await bot.send_message(
            seller_id,
            f"✅ Кто-то принял твоё предложение за <b>{price} ⭐</b>\n\n"
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
    await callback.message.answer("❌ Предложение отклонено.")

    try:
        await bot.send_message(
            seller_id,
            f"❌ Кто-то отклонил твоё предложение.\n\n"
            f"Пользователь: @{callback.from_user.username or callback.from_user.full_name}"
        )
    except:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
