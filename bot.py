import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import Command, CommandStart, CommandObject

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM", "8625418202:AAGqxrkLwIrSuTgWCk0cCJ1yxIvIOJreTQM")
WEB_APP_URL = "https://vercelapp-three-lovat.vercel.app/" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

users_db = dict()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟠 Открыть магазин 🟠", web_app=WebAppInfo(url=WEB_APP_URL))],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🔗 Рефералы")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def cmd_start_handler(message: Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    
    if user_id not in users_db:
        users_db[user_id] = {"refs": 0, "purchases": 0, "inviter": None}
        
        if args and args.isdigit():
            inviter_id = int(args)
            if inviter_id != user_id:
                users_db[user_id]["inviter"] = inviter_id
                if inviter_id in users_db:
                    users_db[inviter_id]["refs"] += 1
                    await bot.send_message(
                        chat_id=inviter_id, 
                        text="🔥 По вашей ссылке зарегистрировался новый пользователь!"
                    )
    
    welcome_text = "⚡️ Добро пожаловать! Нажмите кнопку ниже, чтобы открыть интерактивный магазин."
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user_data = users_db.get(user_id, {"refs": 0, "purchases": 0})
    
    text = f"🍊 Ваш личный кабинет:\n\n" \
           f"ID: {user_id}\n" \
           f"Куплено товаров: {user_data['purchases']}\n" \
           f"Приглашено друзей: {user_data['refs']}"
           
    await message.answer(text)

@dp.message(F.text == "🔗 Рефералы")
async def show_referral_system(message: Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    user_data = users_db.get(user_id, {"refs": 0})
    current_refs = user_data["refs"]
    
    text = f"⚡️ Ваша уникальная ссылка для приглашений:\n" \
           f"{ref_link}\n\n" \
           f"Вы пригласили: {current_refs} чел.\n" \
           f"Отправляйте ссылку друзьям и получайте бонусы за их покупки!"
           
    await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())