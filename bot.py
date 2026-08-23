import asyncio
import os
import time
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM", "8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM")
ADMIN_ID = 7570922005
CARD_NUMBER = "2200701233887170"
STAR_PRICE = 1.48
MIN_STARS = 50

bot = Bot(token=TOKEN)
dp = Dispatcher()

accounts_db = {"random": [], "no_spamblock": [], "spamblock": []}
pending_orders = {}

class AdminState(StatesGroup):
    waiting_for_category = State()
    waiting_for_country = State()
    waiting_for_account_data = State()
    waiting_for_price = State()

class BuyStarsState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_username = State()

class ReviewState(StatesGroup):
    waiting_for_rating = State()
    waiting_for_comment = State()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟠 Купить аккаунты 🟠", callback_data="menu_accounts")],
        [InlineKeyboardButton(text="⭐️ Купить звезды Telegram ⭐️", callback_data="menu_stars")]
    ])

def get_accounts_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟨 Рандом", callback_data="cat_random")],
        [InlineKeyboardButton(text="⚡️ Без спамблока", callback_data="cat_no_spamblock")],
        [InlineKeyboardButton(text="🔥 Со спамблоком", callback_data="cat_spamblock")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def get_sort_menu(category):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Сначала дешевые", callback_data=f"sort_{category}_asc")],
        [InlineKeyboardButton(text="📈 Сначала дорогие", callback_data=f"sort_{category}_desc")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_accounts")]
    ])

def get_pagination_menu(category, sort_type, page):
    items = accounts_db[category]
    if sort_type == "asc":
        items = sorted(items, key=lambda x: x["price"])
    else:
        items = sorted(items, key=lambda x: x["price"], reverse=True)

    per_page = 5
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_items = items[start_idx:end_idx]

    keyboard = []
    for item in current_items:
        btn_text = f"🍊 {item['country']} - {item['price']} руб."
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"buyid_{item['id']}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⏪", callback_data=f"page_{category}_{sort_type}_{page - 1}"))
    if end_idx < len(items):
        nav_buttons.append(InlineKeyboardButton(text="⏩", callback_data=f"page_{category}_{sort_type}_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(text="🔙 Назад к сортировке", callback_data=f"cat_{category}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_menu(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
    ])

def get_admin_confirm_menu(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Подтвердить сделку", callback_data=f"confirm_{order_id}")]
    ])

def get_request_code_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Запросить код", callback_data="req_login_code")]
    ])

def get_rating_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐️ 1", callback_data="rate_1"),
            InlineKeyboardButton(text="⭐️ 2", callback_data="rate_2"),
            InlineKeyboardButton(text="⭐️ 3", callback_data="rate_3"),
            InlineKeyboardButton(text="⭐️ 4", callback_data="rate_4"),
            InlineKeyboardButton(text="⭐️ 5", callback_data="rate_5")
        ]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔥 Добро пожаловать в магазин! Выбирай нужный товар ниже ⚡️", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back_to_main")
async def go_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Главное меню 🟨:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "menu_accounts")
async def show_accounts(call: CallbackQuery):
    await call.message.edit_text("🟠 Выберите категорию аккаунтов:", reply_markup=get_accounts_menu())

@dp.callback_query(F.data.startswith("cat_"))
async def select_sort(call: CallbackQuery):
    category = call.data.replace("cat_", "")
    if not accounts_db[category]:
        await call.answer("В этой категории пока пусто 📭", show_alert=True)
        return
    await call.message.edit_text("Как отсортировать аккаунты? ⚡️", reply_markup=get_sort_menu(category))

@dp.callback_query(F.data.startswith("sort_"))
async def show_first_page(call: CallbackQuery):
    data = call.data.replace("sort_", "")
    if data.endswith("_asc"):
        category = data.replace("_asc", "")
        sort_type = "asc"
    else:
        category = data.replace("_desc", "")
        sort_type = "desc"
        
    await call.message.edit_text("🟠 Выберите аккаунт (Страна/Флаг - Цена):", reply_markup=get_pagination_menu(category, sort_type, 0))

@dp.callback_query(F.data.startswith("page_"))
async def show_page(call: CallbackQuery):
    data = call.data.replace("page_", "")
    parts = data.rsplit("_", 2)
    category = parts[0]
    sort_type = parts[1]
    page = int(parts[2])
    await call.message.edit_text("🟠 Выберите аккаунт:", reply_markup=get_pagination_menu(category, sort_type, page))

@dp.callback_query(F.data.startswith("buyid_"))
async def process_specific_account_buy(call: CallbackQuery):
    acc_id = call.data.replace("buyid_", "")
    
    selected_acc = None
    for cat, accs in accounts_db.items():
        for acc in accs:
            if acc["id"] == acc_id:
                selected_acc = acc
                break
        if selected_acc:
            break
            
    if not selected_acc:
        await call.answer("Этот аккаунт уже куплен или удален ❌", show_alert=True)
        return
        
    price = selected_acc["price"]
    order_id = str(int(time.time())) + str(call.from_user.id)
    
    pending_orders[order_id] = {
        "user_id": call.from_user.id,
        "type": "account",
        "category": selected_acc["category"],
        "acc_id": acc_id,
        "price": price,
        "username": call.from_user.username
    }
    
    text = f"🔥 Вы выбрали аккаунт ({selected_acc['country']}).\nК оплате: 🍊 {price} руб.\nПеревод на карту: {CARD_NUMBER}\nПосле перевода нажмите кнопку."
    await call.message.edit_text(text, reply_markup=get_payment_menu(order_id))

@dp.callback_query(F.data == "menu_stars")
async def buy_stars(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(f"⭐️ Количество звезд (От {MIN_STARS} шт. Курс {STAR_PRICE} руб):")
    await state.set_state(BuyStarsState.waiting_for_amount)

@dp.message(BuyStarsState.waiting_for_amount)
async def process_stars_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return
    amount = int(message.text)
    if amount < MIN_STARS:
        await message.answer(f"Минимум {MIN_STARS} звезд ⚠️")
        return
    await state.update_data(stars_amount=amount)
    await message.answer("🟠 Юзернейм получателя звезд:")
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
    
    text = f"⚡️ Оплата 🍊 {total_price} руб за ⭐️ {amount} звезд.\nКарта: {CARD_NUMBER}\nЖмите кнопку после оплаты."
    await message.answer(text, reply_markup=get_payment_menu(order_id))
    await state.clear()

@dp.callback_query(F.data.startswith("paid_"))
async def check_payment(call: CallbackQuery):
    order_id = call.data.replace("paid_", "")
    order = pending_orders.get(order_id)
    
    if not order:
        await call.answer("Заказ не найден ❌", show_alert=True)
        return
        
    admin_text = f"🔥 Оплата!\n@{order['username']} (ID: {order['user_id']})\nСумма: {order['price']} руб.\nТип: {order['type']}\n"
    if order['type'] == 'stars':
        admin_text += f"Количество: ⭐️ {order['amount']}\nПолучатель: {order['target_user']}"
    elif order['type'] == 'account':
        admin_text += f"ID аккаунта: {order['acc_id']}"
        
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=get_admin_confirm_menu(order_id))
    await call.message.edit_text("⏳ Запрос у администратора. Ожидайте.")

@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_order(call: CallbackQuery):
    order_id = call.data.replace("confirm_", "")
    order = pending_orders.get(order_id)
    
    if not order:
        await call.answer("Заказ не найден ❌", show_alert=True)
        return
        
    user_id = order["user_id"]
    
    if order["type"] == "account":
        cat = order["category"]
        acc_id = order["acc_id"]
        
        acc_data = None
        for i, acc in enumerate(accounts_db[cat]):
            if acc["id"] == acc_id:
                acc_data = accounts_db[cat].pop(i)
                break
                
        if not acc_data:
            await call.message.answer("Этот аккаунт уже продан! ⚠️")
            return
            
        msg_to_user = f"🔥 Подтверждено!\nДанные: {acc_data['data']}\nСтрана: {acc_data['country']}"
        await bot.send_message(chat_id=user_id, text=msg_to_user, reply_markup=get_request_code_menu())
        
    elif order["type"] == "stars":
        await bot.send_message(chat_id=user_id, text=f"⚡️ Заказ выполнен! Звезды отправлены {order['target_user']}.")
        
    await bot.send_message(chat_id=user_id, text="🟠 Оцените сервис:", reply_markup=get_rating_menu())
    del pending_orders[order_id]
    await call.message.edit_text(f"✅ Заказ {order_id} закрыт.")

@dp.callback_query(F.data == "req_login_code")
async def request_code(call: CallbackQuery):
    await bot.send_message(chat_id=ADMIN_ID, text=f"🔑 @{call.from_user.username} запрашивает код для входа.")
    await call.answer("Запрос отправлен ⚡️", show_alert=True)

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
    
    await bot.send_message(chat_id=ADMIN_ID, text=f"📩 Отзыв от @{message.from_user.username}\nОценка: ⭐️ {rating}\nТекст: {message.text}")
    await message.answer("🔥 Отзыв отправлен. Спасибо!")
    await state.clear()

@dp.message(Command("add"))
async def admin_add_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟨 Рандом", callback_data="addcat_random")],
        [InlineKeyboardButton(text="⚡️ Без спамблока", callback_data="addcat_no_spamblock")],
        [InlineKeyboardButton(text="🔥 Со спамблоком", callback_data="addcat_spamblock")]
    ])
    await message.answer("🟠 Категория для пополнения:", reply_markup=kb)
    await state.set_state(AdminState.waiting_for_category)

@dp.callback_query(AdminState.waiting_for_category, F.data.startswith("addcat_"))
async def admin_cat_chosen(call: CallbackQuery, state: FSMContext):
    category = call.data.replace("addcat_", "")
    await state.update_data(target_category=category)
    await call.message.edit_text("🍊 Страна/Флаг:")
    await state.set_state(AdminState.waiting_for_country)

@dp.message(AdminState.waiting_for_country)
async def admin_country_saved(message: Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("⚡️ Данные аккаунта:")
    await state.set_state(AdminState.waiting_for_account_data)

@dp.message(AdminState.waiting_for_account_data)
async def admin_ask_price(message: Message, state: FSMContext):
    await state.update_data(acc_data=message.text)
    await message.answer("🟨 Цена аккаунта (число):")
    await state.set_state(AdminState.waiting_for_price)

@dp.message(AdminState.waiting_for_price)
async def admin_save_account(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return
        
    price = int(message.text)
    data = await state.get_data()
    category = data.get("target_category")
    country = data.get("country")
    acc_data = data.get("acc_data")
    
    acc_id = str(int(time.time() * 1000))
    
    accounts_db[category].append({
        "id": acc_id,
        "country": country,
        "data": acc_data,
        "price": price,
        "category": category
    })
    
    await message.answer("✅ Аккаунт добавлен.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())