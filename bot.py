import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM"
ADMIN_ID = 7570922005
CARD_NUMBER = "2200701233887170"
STAR_PRICE = 1.48
MIN_STARS = 50

bot = Bot(token=TOKEN)
dp = Dispatcher()

accounts_db = {"random": [], "no_spamblock": [], "spamblock": []}
prices = {"random": 45, "no_spamblock": 55, "spamblock": 30}

class AdminState(StatesGroup):
    waiting_for_category = State()
    waiting_for_account_data = State()

class BuyStarsState(StatesGroup):
    waiting_for_amount = State()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить аккаунты", callback_data="menu_accounts")],
        [InlineKeyboardButton(text="Купить звезды Telegram", callback_data="menu_stars")]
    ])

def get_accounts_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Рандом ({prices['random']} руб)", callback_data="buy_acc_random")],
        [InlineKeyboardButton(text=f"Без спамблока ({prices['no_spamblock']} руб)", callback_data="buy_acc_no_spamblock")],
        [InlineKeyboardButton(text=f"Со спамблоком ({prices['spamblock']} руб)", callback_data="buy_acc_spamblock")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])

def get_payment_menu(item_type, amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я оплатил", callback_data=f"paid_{item_type}_{amount}")],
        [InlineKeyboardButton(text="Отмена", callback_data="back_to_main")]
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
    text = f"К оплате: {price} руб.\nПереведите средства на карту: {CARD_NUMBER}\nПосле успешного перевода нажмите кнопку ниже."
    await call.message.edit_text(text, reply_markup=get_payment_menu(category, price))

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
        
    total_price = round(amount * STAR_PRICE, 2)
    text = f"Вы покупаете {amount} звезд.\nК оплате: {total_price} руб.\nПереведите на карту: {CARD_NUMBER}\nЗатем нажмите кнопку."
    
    await message.answer(text, reply_markup=get_payment_menu("stars", total_price))
    await state.clear()

@dp.callback_query(F.data.startswith("paid_"))
async def check_payment(call: CallbackQuery):
    data = call.data.split("_")
    item_type = data[1]
    amount = data[2]
    
    admin_text = f"Новая оплата!\nПользователь @{call.from_user.username} (ID: {call.from_user.id})\nЗаявляет об оплате {amount} руб за товар: {item_type}."
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    await call.message.edit_text("Запрос отправлен администратору на проверку. Товар будет выдан после подтверждения платежа.")

@dp.message(Command("add"))
async def admin_add_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Рандом", callback_data="addcat_random")],
        [InlineKeyboardButton(text="Без спамблока", callback_data="addcat_no_spamblock")],
        [InlineKeyboardButton(text="Со спамблоком", callback_data="addcat_spamblock")]
    ])
    await message.answer("Выберите категорию для пополнения базы аккаунтов:", reply_markup=kb)
    await state.set_state(AdminState.waiting_for_category)

@dp.callback_query(AdminState.waiting_for_category, F.data.startswith("addcat_"))
async def admin_cat_chosen(call: CallbackQuery, state: FSMContext):
    category = call.data.replace("addcat_", "")
    await state.update_data(target_category=category)
    await call.message.edit_text("Отправьте данные аккаунта (логин:пароль или ссылку на сессию):")
    await state.set_state(AdminState.waiting_for_account_data)

@dp.message(AdminState.waiting_for_account_data)
async def admin_save_account(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("target_category")
    
    accounts_db[category].append(message.text)
    
    await message.answer(f"Успех! Аккаунт добавлен. Всего в этой категории: {len(accounts_db[category])} шт.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())