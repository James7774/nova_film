from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_reply_keyboard():
    keyboard = [
        [
            KeyboardButton(text="🎬 Kino qo'shish"),
            KeyboardButton(text="🗑 Kinoni o'chirish")
        ],
        [
            KeyboardButton(text="📜 Kinolar ro'yxati"),
            KeyboardButton(text="📊 Statistika")
        ],
        [
            KeyboardButton(text="📢 Reklama tarqatish"),
            KeyboardButton(text="📢 Kanallar sozlamasi")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard, 
        resize_keyboard=True,
        input_field_placeholder="Admin panel menyusini tanlang..."
    )
