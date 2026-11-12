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

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать оффер")],
            [KeyboardButton(text="Подписка"), KeyboardButton(text="Старт")]
        ],
        resize_keyboard=True
    )

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

@dp.message(Command("start"))
@dp.message(F.text == "Старт")
async def start(message: types.Message):
    await message.answer(
        "Бот для создания офферов на подарки Telegram.\n\n"
        "Нажми «Создать оффер» или пришли ссылку на подарок.",
        reply_markup=main_kb()
    )

@dp.message(F.text == "Подписка")
async def subscription_info(message: types.Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("Ты владелец бота. Подписка не нужна.")
        return

    if await is_subscribed(message.from_user.id):
        await message.answer("Подписка активна. Можешь создавать офферы.")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer(
            "Для создания офферов нужно подписаться на канал.",
            reply_markup=kb
        )

@dp.message(F.text == "Создать оффер")
async def create_offer_btn(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer("Сначала подпишись на канал.", reply_markup=kb)
        return

    await message.answer(
        "Пришли ссылку на подарок:\n"
        "<code>https://t.me/nft/Название-123</code>"
    )

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
                "Формат:\n<code>/offer ссылка цена валюта</code>\n\n"
                "Пример:\n<code>/offer https://t.me/nft/Gift-123 123 stars</code>"
            )
            return

        link = parts[1]
        price = parts[2]
        currency = parts[3].lower()

        if not re.match(r"https?://t\.me/nft/\S+", link):
            await message.answer("Неверная ссылка")
            return
        if not price.isdigit():
            await message.answer("Цена должна быть числом")
            return
        if currency not in ["stars", "gram", "ton"]:
            await message.answer("Валюта: stars, gram или ton")
            return

        currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}[currency]
        gift_name = link.split("/")[-1].replace("-", " #")

        text = (
            f"<b>с помощью @{ (await bot.get_me()).username }</b>\n\n"
            f"<a href='{link}'>ПОКАЗАТЬ ПОДАРОК</a>\n\n"
            f"<b>{message.from_user.full_name}</b> предлагает Вам\n"
            f"<b>{price} {currency_text}</b> за подарок <b>{gift_name}</b>.\n\n"
            f"Предложение действует ещё 24 часа"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", url=link)],
            [
                InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{message.from_user.id}"),
                InlineKeyboardButton(text="Принять", callback_data=f"accept:{message.from_user.id}:{price}:{currency}:{link}")
            ]
        ])

        try:
            await message.delete()
        except:
            pass

        await message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)

    except Exception:
        await message.answer("Ошибка. Проверь формат.")

@dp.message(F.text.regexp(r"https?://t\.me/nft/\S+"))
async def got_link(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/popapisa000")]
        ])
        await message.answer("Сначала подпишись на канал.", reply_markup=kb)
        return

    await state.update_data(link=message.text.strip())
    await state.set_state(OfferState.waiting_for_price)
    await message.answer("Введи цену (только число):")

@dp.message(OfferState.waiting_for_price)
async def got_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Нужно только число:")
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

    currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}[currency]
    gift_name = link.split("/")[-1].replace("-", " #")

    text = (
        f"<b>с помощью @{ (await bot.get_me()).username }</b>\n\n"
        f"<a href='{link}'>ПОКАЗАТЬ ПОДАРОК</a>\n\n"
        f"<b>{callback.from_user.full_name}</b> предлагает Вам\n"
        f"<b>{price} {currency_text}</b> за подарок <b>{gift_name}</b>.\n\n"
        f"Предложение действует ещё 24 часа"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", url=link)],
        [
            InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{callback.from_user.id}"),
            InlineKeyboardButton(text="Принять", callback_data=f"accept:{callback.from_user.id}:{price}:{currency}:{link}")
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
    link = parts[4] if len(parts) > 4 else ""
    currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}.get(currency, currency)
    gift_name = link.split("/")[-1].replace("-", " #") if link else "подарок"

    # Всплывающее окно
    await callback.answer(
        "Предложение о продаже принято.\n\n"
        "Следующий этап — передача подарка покупателю. "
        "Оплата станет доступна после подтверждения получения.",
        show_alert=True
    )

    # Обновляем сообщение
    new_text = (
