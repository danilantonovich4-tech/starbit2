import asyncio
import os
import time
import json
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

# Задавайте токен через переменную окружения BOT_TOKEN, не храните его в коде.
TOKEN = os.getenv("8625418202:AAHlq3Rz_nUNEQ25d1iw83TE3OpxppA8U1U", "8625418202:AAHlq3Rz_nUNEQ25d1iw83TE3OpxppA8U1U")
ADMIN_ID = 7570922005
CARD_NUMBER = "2200701233887170"
STAR_PRICE = 1.48
MIN_STARS = 50

WEBAPP_URL = "https://vercelapp-three-lovat.vercel.app/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

pending_orders = {}


class ReviewState(StatesGroup):
    waiting_for_comment = State()


class ReceiptState(StatesGroup):
    waiting_for_receipt = State()


def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Купить звезды Telegram", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])


def get_cancel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
    ])


def get_admin_confirm_menu(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Подтвердить сделку", callback_data=f"confirm_{order_id}")]
    ])


def get_rating_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐️ 1", callback_data="rate_1"),
            InlineKeyboardButton(text="⭐️ 2", callback_data="rate_2"),
            InlineKeyboardButton(text="⭐️ 3", callback_data="rate_3"),
            InlineKeyboardButton(text="⭐️ 4", callback_data="rate_4"),
            InlineKeyboardButton(text="⭐️ 5", callback_data="rate_5"),
        ]
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🟣 Добро пожаловать в gudet stars!\nНажми на кнопку ниже, чтобы выбрать количество звёзд.",
        reply_markup=get_main_menu()
    )


@dp.callback_query(F.data == "back_to_main")
async def go_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Главное меню 🟣:", reply_markup=get_main_menu())


@dp.message(F.web_app_data)
async def process_webapp_order(message: Message, state: FSMContext):
    """Заказ, пришедший из мини-приложения (index.html)."""
    try:
        data = json.loads(message.web_app_data.data)
    except (ValueError, AttributeError):
        await message.answer("⚠️ Не удалось прочитать заказ, попробуйте ещё раз через кнопку ниже.",
                              reply_markup=get_main_menu())
        return

    amount = int(data.get("amount", 0))
    target_username = str(data.get("target_username", "")).lstrip("@")
    price = data.get("price")

    if amount < MIN_STARS or not target_username:
        await message.answer(f"⚠️ Некорректный заказ. Минимум {MIN_STARS} звёзд и указанный юзернейм.",
                              reply_markup=get_main_menu())
        return

    if not isinstance(price, (int, float)):
        price = round(amount * STAR_PRICE, 2)

    order_id = str(int(time.time())) + str(message.from_user.id)
    pending_orders[order_id] = {
        "user_id": message.from_user.id,
        "amount": amount,
        "target_user": target_username,
        "price": price,
        "username": message.from_user.username,
    }

    text = (
        f"⚡️ Оплата 🟣 {price} руб за ⭐️ {amount} звезд.\n"
        f"Получатель: @{target_username}\n"
        f"Карта: {CARD_NUMBER}\n\n"
        f"После перевода пришлите сюда скриншот чека 📸 (просто отправьте фото в этот чат)."
    )
    await message.answer(text, reply_markup=get_cancel_menu())
    await state.update_data(order_id=order_id)
    await state.set_state(ReceiptState.waiting_for_receipt)


@dp.message(ReceiptState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = pending_orders.get(order_id)

    if not order:
        await message.answer("⚠️ Заказ не найден, начните заново.", reply_markup=get_main_menu())
        await state.clear()
        return

    admin_caption = (
        f"🧾 Чек на проверку\n"
        f"@{order['username']} (ID: {order['user_id']})\n"
        f"Сумма: {order['price']} руб.\n"
        f"Количество: ⭐️ {order['amount']}\n"
        f"Получатель: @{order['target_user']}"
    )
    largest_photo = message.photo[-1]
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=largest_photo.file_id,
        caption=admin_caption,
        reply_markup=get_admin_confirm_menu(order_id)
    )
    await message.answer("⏳ Чек отправлен на проверку администратору. Ожидайте.")
    await state.clear()


@dp.message(ReceiptState.waiting_for_receipt)
async def process_receipt_wrong_type(message: Message):
    await message.answer("📸 Пришлите именно фото (скриншот чека), не текст и не файл.")


@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_order(call: CallbackQuery):
    order_id = call.data.replace("confirm_", "")
    order = pending_orders.get(order_id)

    if not order:
        await call.answer("Заказ не найден ❌", show_alert=True)
        return

    user_id = order["user_id"]
    await bot.send_message(chat_id=user_id, text=f"⚡️ Заказ выполнен! Звезды отправлены @{order['target_user']}.")
    await bot.send_message(chat_id=user_id, text="🟣 Оцените сервис:", reply_markup=get_rating_menu())

    del pending_orders[order_id]
    await call.message.edit_text(f"✅ Заказ {order_id} закрыт.")


@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(call: CallbackQuery, state: FSMContext):
    rating = call.data.replace("rate_", "")
    await state.update_data(rating=rating)
    await call.message.edit_text("📝 Напишите текстовый отзыв:")
    await state.set_state(ReviewState.waiting_for_comment)


@dp.message(ReviewState.waiting_for_comment)
async def process_review_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    rating = data.get("rating")

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 Отзыв от @{message.from_user.username}\nОценка: ⭐️ {rating}\nТекст: {message.text}"
    )
    await message.answer("🟣 Отзыв отправлен. Спасибо!")
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())