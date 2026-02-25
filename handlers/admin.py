from aiogram import Router, F, types, Bot
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging
import re
import html
import asyncio
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

from keyboards.inline import get_admin_panel
from keyboards.reply import get_admin_reply_keyboard
from database.db import add_video, delete_code, get_all_codes, get_global_stats, get_all_users, save_broadcast_message, get_broadcast_messages
from utils.states import AdminStates
from config import ADMINS

admin_router = Router()

# Admin check filter
admin_router.message.filter(F.from_user.id.in_(ADMINS))
admin_router.callback_query.filter(F.from_user.id.in_(ADMINS))

def is_menu_button(text):
    return text in ["🎬 Kino qo'shish", "🗑 Kinoni o'chirish", "📜 Kinolar ro'yxati", "📊 Statistika", "📢 Reklama tarqatish", "📝 Shablon"]

@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👨‍💻 <b>Admin Panel</b>\n\nXush kelibsiz, Admin! Quyidagi menyudan foydalanishingiz mumkin:",
        reply_markup=get_admin_reply_keyboard(),
        parse_mode="HTML"
    )

# --- Adding Movie Flow ---
@admin_router.message(F.text == "🎬 Kino qo'shish")
async def btn_admin_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔢 <b>Kino uchun kodni kiriting (masalan: 123):</b>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_code)

@admin_router.message(AdminStates.waiting_for_code)
async def process_admin_code(message: types.Message, state: FSMContext):
    if is_menu_button(message.text):
        await state.clear()
        return

    code = message.text.strip()
    await state.update_data(code=code)
    await message.answer(
        f"✅ Kod saqlandi: <b>{html.escape(code)}</b>\n\n"
        f"Endi ushbu kod uchun kinoni yuboring.\n\n"
        f"🎥 <b>Eslatma:</b> Kinoni o'z kanalingizdan <b>Forward</b> qilishingiz yoki to'g'ridan-to'g'ri fayl sifatida yuborishingiz mumkin.",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_channel_post)

@admin_router.message(AdminStates.waiting_for_channel_post)
async def process_channel_post(message: types.Message, state: FSMContext, bot: Bot):
    if is_menu_button(message.text):
        await state.clear()
        return

    storage_channel_id = None
    storage_message_id = None
    file_id = None
    file_type = 'video'

    if message.forward_from_chat:
        storage_channel_id = message.forward_from_chat.id
        storage_message_id = message.forward_from_message_id
    
    if message.video:
        file_id = message.video.file_id
        file_type = 'video'
    elif message.document and (message.document.mime_type and message.document.mime_type.startswith('video')):
        file_id = message.document.file_id
        file_type = 'document'
    elif message.animation:
        file_id = message.animation.file_id
        file_type = 'animation'

    if not file_id and not storage_channel_id:
        await message.answer("❌ Xatolik! Iltimos, video faylni yuboring yoki kanaldan forward qiling.")
        return

    await state.update_data(
        storage_channel_id=str(storage_channel_id) if storage_channel_id else None,
        storage_message_id=storage_message_id,
        file_id=file_id,
        file_type=file_type
    )
    await message.answer("📝 <b>Video uchun tavsif (caption) kiriting:</b>\n\nUshbu matn video ostida foydalanuvchiga ko'rinadi.", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_title)

@admin_router.message(AdminStates.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    if is_menu_button(message.text):
        await state.clear()
        return

    data = await state.get_data()
    description = message.text
    
    await add_video(
        code=data['code'],
        title=description,
        quality="", 
        file_id=data.get('file_id'),
        file_type=data.get('file_type', 'video'),
        expires_at=data.get('expires_at'),
        storage_channel_id=data.get('storage_channel_id'),
        storage_message_id=data.get('storage_message_id')
    )
    
    await message.answer(
        f"✅ <b>Muvaffaqiyatli yakunlandi!</b>\n\n"
        f"Kino <code>{html.escape(data['code'])}</code> kodi bilan bazaga qo'shildi.",
        parse_mode="HTML"
    )
    await state.clear()

# --- Deleting Movie ---
@admin_router.message(F.text == "🗑 Kinoni o'chirish")
async def btn_admin_delete_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🗑 O'chirmoqchi bo'lgan kino kodini yuboring:")
    await state.set_state(AdminStates.waiting_for_code_delete)

@admin_router.message(AdminStates.waiting_for_code_delete)
async def process_admin_delete(message: types.Message, state: FSMContext):
    if is_menu_button(message.text):
        await state.clear()
        return
    code = message.text.strip()
    await delete_code(code)
    await message.answer(f"✅ Kod <code>{html.escape(code)}</code> o'chirildi.", parse_mode="HTML")
    await state.clear()

# --- List and Stats ---
@admin_router.message(F.text == "📜 Kinolar ro'yxati")
async def btn_admin_list(message: types.Message, state: FSMContext):
    await state.clear()
    codes = await get_all_codes()
    if not codes:
        await message.answer("📭 Hozircha kinolar qo'shilmagan.")
    else:
        text = "📜 <b>Barcha kinolar:</b>\n\n"
        for code, title in codes:
            text += f"• <code>{code}</code> - {html.escape(title)}\n"
        await message.answer(text, parse_mode="HTML")

@admin_router.message(F.text == "📊 Statistika")
async def btn_admin_stats(message: types.Message, state: FSMContext):
    await state.clear()
    users, videos = await get_global_stats()
    await message.answer(
        f"📊 <b>Bot Statistikasi:</b>\n\n"
        f"👤 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {videos}\n",
        parse_mode="HTML"
    )

# --- Broadcast Feature ---
@admin_router.message(F.text == "📢 Reklama tarqatish")
async def btn_broadcast_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📢 <b>Reklama tarqatish bo'limi</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n"
        "Xabar matn, rasm, video yoki forward bo'lishi mumkin.",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast)

@admin_router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    if is_menu_button(message.text):
        await state.clear()
        return

    users = await get_all_users()
    count = 0
    blocked = 0
    broadcast_id = f"brd_{int(datetime.now().timestamp())}"
    
    status_msg = await message.answer(f"⏳ Tarqatish boshlandi: 0/{len(users)}")
    
    for user_id in users:
        try:
            sent = await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            await save_broadcast_message(broadcast_id, user_id, sent.message_id)
            count += 1
        except Exception:
            blocked += 1
        
        # Update status every 50 users to avoid flooding
        if (count + blocked) % 50 == 0:
            try:
                await status_msg.edit_text(f"⏳ Tarqatish jarayoni: {count + blocked}/{len(users)}")
            except Exception:
                pass
        
        # Small delay to avoid Telegram limits
        await asyncio.sleep(0.05)

    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Hammaning telegramidan o'chirish", callback_data=f"del_brd:{broadcast_id}")
    
    await status_msg.edit_text(
        f"✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"👤 Jami foydalanuvchilar: {len(users)}\n"
        f"✅ Muvaffaqiyatli bordi: {count}\n"
        f"❌ Botni bloklaganlar: {blocked}\n\n"
        f"☝️ <i>Xato ketgan bo'lsa, quyidagi tugma orqali o'chirib yuborishingiz mumkin:</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.clear()

@admin_router.callback_query(F.data.startswith("del_brd:"))
async def cb_delete_broadcast(callback: types.CallbackQuery, bot: Bot):
    broadcast_id = callback.data.split(":")[1]
    messages = await get_broadcast_messages(broadcast_id)
    
    await callback.message.edit_text(f"⏳ O'chirish boshlandi: 0/{len(messages)}")
    
    count = 0
    for user_id, msg_id in messages:
        try:
            await bot.delete_message(chat_id=user_id, message_id=msg_id)
            count += 1
        except Exception:
            pass
        
        if count % 50 == 0:
            try:
                await callback.message.edit_text(f"⏳ O'chirilmoqda: {count}/{len(messages)}")
            except Exception:
                pass
        
        await asyncio.sleep(0.05)
    
    await callback.message.edit_text(f"✅ <b>Reklama barcha foydalanuvchilardan o'chirib yuborildi!</b>\n\nJami o'chirildi: {count}", parse_mode="HTML")
    await callback.answer()

# --- Template Feature ---
@admin_router.message(F.text == "📝 Shablon")
async def btn_admin_template(message: types.Message, state: FSMContext):
    await state.clear()
    template = (
        "🎬 <b>Nomi:</b> \n"
        "🌍 <b>Tili:</b> O'zbek\n"
        "⭐️ <b>Reyting:</b> 5\n"
        "⏳ <b>Davomiyligi:</b> \n\n"
        "📖 <b>Qisqacha mazmun:</b> \n"
        "________________________\n\n"
        "🔐 <b>Kod:</b> "
    )
    await message.answer(
        "📝 <b>Kino uchun tavsif shabloni:</b>\n\n"
        f"<code>{template}</code>\n\n"
        "☝️ <i>Shablon ustiga bossangiz u nusxalanadi. Uni nusxalab olib, kerakli joylarni to'ldirib, kino qo'shish vaqtida tavsif sifatida yuborishingiz mumkin.</i>",
        parse_mode="HTML"
    )
