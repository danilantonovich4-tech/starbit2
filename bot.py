import asyncio
import os
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = os.getenv("8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM", "8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM")
ADMIN_ID = 7570922005
CARD_NUMBER = "2200701233887170"
STAR_PRICE = 1.48
MIN_STARS = 50

bot = Bot(token=TOKEN)
dp = Dispatcher()

""" База данных в памяти """
accounts_db = {"random": [], "no_spamblock": [], "spamblock": []}
prices = {"random": 45, "no_spamblock": 55, "spamblock": 30}
pending_orders = {}

class AdminState(StatesGroup):
    waiting_for_category = State()
    waiting_for_country = State()
    waiting_for_account_data = State()

class BuyStarsState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_username = State()

class ReviewState(StatesGroup):
    waiting_for_rating = State()
    waiting_for_comment = State()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить аккаунты", callback_data="menu_accounts")],
        [InlineKeyboardButton(text="Купить звезды Telegram", callback_data="menu_stars")]
    ])

def get_accounts_menu():
    """ Цены из кнопок убраны, как ты и просил """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Рандом", callback_data="buy_acc_random")],
        [InlineKeyboardButton(text="Без спамблока", callback_data="buy_acc_no_spamblock")],
        [InlineKeyboardButton(text="Со спамблоком", callback_data="buy_acc_spamblock")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])

def get_payment_menu(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я оплатил", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="back_to_main")]
    ])

def get_admin_confirm_menu(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить сделку", callback_data=f"admin_confirm_{order_id}")]
    ])

def get_request_code_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запросить код", callback_data="req_login_code")]
    ])

def get_rating_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="rate_1"),
            InlineKeyboardButton(text="2", callback_data="rate_2"),
            InlineKeyboardButton(text="3", callback_data="rate_3"),
            InlineKeyboardButton(text="4", callback_data="rate_4"),
            InlineKeyboardButton(text="5", callback_data="rate_5")
        ]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добро пожаловать в магазин! Выберите нужный раздел:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back_to_main")
async def go_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Главное меню:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "menu_accounts")
async def show_accounts(call: CallbackQuery):
    await call.message.edit_text("Выберите категорию аккаунтов:", reply_markup=get_accounts_menu())

@dp.callback_query(F.data.startswith("buy_acc_"))
async def process_account_buy(call: CallbackQuery):
    category = call.data.replace("buy_acc_", "")
    
    if not accounts_db[category]:
        await call.answer("К сожалению, эти аккаунты закончились!", show_alert=True)
        return
        
    price = prices[category]
    order_id = str(int(time.time())) + str(call.from_user.id)
    
    pending_orders[order_id] = {
        "user_id": call.from_user.id,
        "type": "account",
        "category": category,
        "price": price,
        "username": call.from_user.username
    }
    
    text = f"К оплате: {price} руб.\nПереведите средства на карту: {CARD_NUMBER}\nПосле успешного перевода нажмите кнопку ниже."
    await call.message.edit_text(text, reply_markup=get_payment_menu(order_id))

@dp.callback_query(F.data == "menu_stars")
async def buy_stars(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(f"Введите количество звезд для покупки.\nМинимум: {MIN_STARS} шт.\nКурс: 1 звезда = {STAR_PRICE} руб.")
    await state.set_state(BuyStarsState.waiting_for_amount)

@dp.message(BuyStarsState.waiting_for_amount)
async def process_stars_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
        
    amount = int(message.text)
    
    if amount < MIN_STARS:
        await message.answer(f"Минимальная сумма покупки — {MIN_STARS} звезд. Попробуйте еще раз:")
        return
        
    await state.update_data(stars_amount=amount)
    await message.answer("Отправьте юзернейм человека, которому нужно купить звезды:")
    await state.set_state(BuyStarsState.waiting_for_username)

@dp.message(BuyStarsState.waiting_for_username)
async def process_stars_username(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("stars_amount")
    target_username = message.text
    
    total_price = round(amount * STAR_PRICE, 2)
    order_id = str(int(time.time())) + str(message.from_user.id)
    
    pending_orders[order_id] = {
        "user_id": message.from_user.id,
        "type": "stars",
        "amount": amount,
        "target_user": target_username,
        "price": total_price,
        "username": message.from_user.username
    }
    
    text = f"Покупка {amount} звезд для {target_username}.\nК оплате: {total_price} руб.\nПереведите на карту: {CARD_NUMBER}\nЗатем нажмите кнопку."
    await message.answer(text, reply_markup=get_payment_menu(order_id))
    await state.clear()

@dp.callback_query(F.data.startswith("paid_"))
async def check_payment(call: CallbackQuery):
    order_id = call.data.replace("paid_", "")
    order = pending_orders.get(order_id)
    
    if not order:
        await call.answer("Заказ не найден или уже обработан.", show_alert=True)
        return
        
    admin_text = f"Новая оплата!\nПользователь @{order['username']} (ID: {order['user_id']})\nОплатил {order['price']} руб.\nТип: {order['type']}\n"
    if order['type'] == 'stars':
        admin_text += f"Количество: {order['amount']} звезд\nПолучатель: {order['target_user']}"
    elif order['type'] == 'account':
        admin_text += f"Категория: {order['category']}"
        
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=get_admin_confirm_menu(order_id))
    await call.message.edit_text("Запрос отправлен администратору. Ожидайте выдачи товара.")

@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_order(call: CallbackQuery):
    order_id = call.data.replace("admin_confirm_", "")
    order = pending_orders.get(order_id)
    
    if not order:
        await call.answer("Ошибка: Заказ не найден.", show_alert=True)
        return
        
    user_id = order["user_id"]
    
    if order["type"] == "account":
        cat = order["category"]
        if not accounts_db[cat]:
            await call.message.answer("В базе нет аккаунтов этой категории!")
        else:
            acc_data = accounts_db[cat].pop(0)
            msg_to_user = f"Ваш заказ подтвержден!\nДанные аккаунта: {acc_data['data']}\nСтрана/Флаг: {acc_data['country']}"
            await bot.send_message(chat_id=user_id, text=msg_to_user, reply_markup=get_request_code_menu())
    elif order["type"] == "stars":
        msg_to_user = f"Ваш заказ подтвержден! {order['amount']} звезд отправлены пользователю {order['target_user']}."
        await bot.send_message(chat_id=user_id, text=msg_to_user)
        
    await bot.send_message(chat_id=user_id, text="Пожалуйста, оцените наш сервис от 1 до 5 звезд:", reply_markup=get_rating_menu())
    
    del pending_orders[order_id]
    await call.message.edit_text(f"Сделка по заказу {order_id} закрыта.")

@dp.callback_query(F.data == "req_login_code")
async def request_code(call: CallbackQuery):
    await bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь @{call.from_user.username} (ID: {call.from_user.id}) запрашивает код для входа в купленный аккаунт.")
    await call.answer("Запрос кода отправлен админу. Ожидайте сообщение.", show_alert=True)

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(call: CallbackQuery, state: FSMContext):
    rating = call.data.replace("rate_", "")
    await state.update_data(rating=rating)
    await call.message.edit_text("Спасибо за оценку! Теперь напишите небольшой текстовый отзыв о нашем сервисе:")
    await state.set_state(ReviewState.waiting_for_comment)

@dp.message(ReviewState.waiting_for_comment)
async def process_review_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    rating = data.get("rating")
    comment = message.text
    
    review_text = f"Новый отзыв!\nОт: @{message.from_user.username}\nОценка: {rating} звезд\nОтзыв: {comment}"
    await bot.send_message(chat_id=ADMIN_ID, text=review_text)
    
    await message.answer("Ваш отзыв успешно отправлен. Спасибо за покупку!")
    await state.clear()

@dp.message(Command("add"))
async def admin_add_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Рандом", callback_data="addcat_random")],
        [InlineKeyboardButton(text="Без спамблока", callback_data="addcat_no_spamblock")],
        [InlineKeyboardButton(text="Со спамблоком", callback_data="addcat_spamblock")]
    ])
    await message.answer("Выберите категорию для пополнения:", reply_markup=kb)
    await state.set_state(AdminState.waiting_for_category)

@dp.callback_query(AdminState.waiting_for_category, F.data.startswith("addcat_"))
async def admin_cat_chosen(call: CallbackQuery, state: FSMContext):
    category = call.data.replace("addcat_", "")
    await state.update_data(target_category=category)
    await call.message.edit_text("Введите страну и номер (или флаг) для этого аккаунта:")
    await state.set_state(AdminState.waiting_for_country)

@dp.message(AdminState.waiting_for_country)
async def admin_country_saved(message: Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("Отлично. Теперь отправьте данные самого аккаунта (сессия или логин:пароль):")
    await state.set_state(AdminState.waiting_for_account_data)

@dp.message(AdminState.waiting_for_account_data)
async def admin_save_account(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("target_category")
    country = data.get("country")
    
    accounts_db[category].append({"data": message.text, "country": country})
    
    await message.answer(f"Аккаунт успешно добавлен в базу (категория: {category}).")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
