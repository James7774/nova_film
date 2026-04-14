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
from database.db import add_video, delete_code, get_all_codes, get_global_stats, get_all_users, save_broadcast_message, get_broadcast_messages, get_all_channels, add_channel, delete_channel, update_channel_title, get_video_by_code, check_code_exists
from utils.states import AdminStates
from config import ADMINS

admin_router = Router()

# Admin check filter
admin_router.message.filter(F.from_user.id.in_(ADMINS))
admin_router.callback_query.filter(F.from_user.id.in_(ADMINS))

def is_menu_button(text):
    return text in ["🎬 Kino qo'shish", "🗑 Kinoni o'chirish", "📜 Kinolar ro'yxati", "📊 Statistika", "📢 Reklama tarqatish", "📢 Kanallar sozlamasi"]

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
    
    # Check if code already exists
    logger.info(f"Admin checking code: {code}")
    exists = await check_code_exists(code)
    if exists:
        logger.info(f"Code '{code}' already exists in database.")
        await message.answer(
            f"⚠️ <b>Bu kod allaqachon mavjud!</b>\n\n"
            f"Kod <code>{html.escape(code)}</code> bazada bor.\n"
            f"Iltimos, boshqa kod kiriting:",
            parse_mode="HTML"
        )
        return
    
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

    caption = message.caption or ""
    await state.update_data(
        storage_channel_id=str(storage_channel_id) if storage_channel_id else None,
        storage_message_id=storage_message_id,
        file_id=file_id,
        file_type=file_type,
        caption=caption
    )
    
    msg = "📝 <b>Video uchun tavsif (caption) kiriting:</b>\n\n"
    if caption:
        msg += f"<i>Hozirgi tavsif:</i>\n<code>{html.escape(caption)}</code>\n\n"
        msg += "Ushbu tavsifni qoldirish uchun /skip bosing yoki yangi tavsif yozing."
    else:
        msg += "Ushbu matn video ostida foydalanuvchiga ko'rinadi."
        
    await message.answer(msg, parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_title)

@admin_router.message(AdminStates.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    if is_menu_button(message.text):
        await state.clear()
        return

    data = await state.get_data()
    description = message.text
    logger.info(f"Admin providing caption for code {data.get('code')}: {description[:50]}...")
    
    if description == "/skip":
        description = data.get('caption', '')
        if not description:
            await message.answer("❌ Video captionga ega emas! Iltimos, tavsif kiriting.")
            return

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
    
    # Extract short title for confirmation
    short_title = description.split('\n')[0].replace('🎬 Nomi:', '').strip()
    
    await message.answer(
        f"✅ <b>Muvaffaqiyatli yakunlandi!</b>\n\n"
        f"🎬 <b>Nomi:</b> {html.escape(short_title)}\n"
        f"🔐 <b>Kodi:</b> <code>{html.escape(data['code'])}</code>\n\n"
        f"Kino muvaffaqiyatli bazaga qo'shildi.",
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
    logger.info(f"Admin attempt to delete code: {code}")
    
    exists = await check_code_exists(code)
    if not exists:
        await message.answer(f"❌ <b>Kod topilmadi!</b>\n\nBazaviy kod <code>{html.escape(code)}</code> topilmadi.", parse_mode="HTML")
        await state.clear()
        return

    await delete_code(code)
    logger.info(f"Code {code} deleted successfully by admin {message.from_user.id}")
    await message.answer(f"✅ Kod <code>{html.escape(code)}</code> muvaffaqiyatli o'chirildi.", parse_mode="HTML")
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
            # Faqat eng birinchi mazmunli qatorni (nomini) olish
            name = ""
            for line in title.split('\n'):
                clean = line.strip()
                if clean and not clean.startswith(('🌍', '⭐', '⏳', '📖', '🔐', '___')):
                    # Emojilar va 'Nomi:' ni olib tashlash
                    clean = clean.replace('🎬', '').replace('Nomi:', '').strip()
                    if clean:
                        name = clean
                        break
            if not name:
                name = title[:25]
            text += f"• <code>{code}</code> — {html.escape(name)}\n"
        
        # Agar matn juda uzun bo'lsa, uni bo'lib yuborish
        if len(text) > 4096:
            for i in range(0, len(text), 4096):
                await message.answer(text[i:i+4096], parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

@admin_router.message(F.text == "📊 Statistika")
async def btn_admin_stats(message: types.Message, state: FSMContext):
    await state.clear()
    total_users, active_users, videos = await get_global_stats()
    await message.answer(
        f"📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total_users}\n"
        f"✅ Faol foydalanuvchilar: {active_users}\n"
        f"🎬 Kinolar soni: {videos}\n",
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

# --- Dynamic Channels Management ---
@admin_router.message(F.text == "📢 Kanallar sozlamasi")
async def btn_channels_manage(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kanal qo'shish", callback_data="add_ch")
    builder.button(text="📝 Kanallar nomini tahrirlash", callback_data="list_edit_ch")
    builder.button(text="🗑 Kanallarni o'chirish", callback_data="list_del_ch")
    builder.adjust(1)
    
    channels = await get_all_channels()
    msg = "📢 <b>Kanallar sozlamasi</b>\n\n"
    if not channels:
        msg += "Hozircha majburiy obuna kanallari yo'q."
    else:
        msg += "<b>Hozirgi kanallar:</b>\n"
        for ch in channels:
            msg += f"• {ch['title']} ({ch['channel_id']})\n"
            
    await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.callback_query(F.data == "list_del_ch")
async def cb_list_del_channels(callback: types.CallbackQuery):
    channels = await get_all_channels()
    if not channels:
        await callback.answer("O'chirish uchun kanallar yo'q!", show_alert=True)
        return
        
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.button(text=f"🗑 {ch['title']}", callback_data=f"del_ch:{ch['id']}")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_ch_manage")
    builder.adjust(1)
    
    await callback.message.edit_text("🗑 <b>O'chirmoqchi bo'lgan kanalni tanlang:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "list_edit_ch")
async def cb_list_edit_channels(callback: types.CallbackQuery):
    channels = await get_all_channels()
    if not channels:
        await callback.answer("Tahrirlash uchun kanallar yo'q!", show_alert=True)
        return
        
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.button(text=f"✏️ {ch['title']}", callback_data=f"edit_ch:{ch['id']}")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_ch_manage")
    builder.adjust(1)
    
    await callback.message.edit_text("✏️ <b>Nomini o'zgartirmoqchi bo'lgan kanalni tanlang:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("edit_ch:"))
async def cb_edit_channel_select(callback: types.CallbackQuery, state: FSMContext):
    ch_db_id = int(callback.data.split(":")[1])
    await state.update_data(edit_ch_id=ch_db_id)
    await callback.message.answer("📝 <b>Kanal uchun yangi nom kiriting:</b>\n(Masalan: 1 - kanal)")
    await state.set_state(AdminStates.waiting_for_new_channel_title)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_new_channel_title)
async def process_new_ch_title(message: types.Message, state: FSMContext):
    if is_menu_button(message.text):
        await state.clear()
        return
    data = await state.get_data()
    new_title = message.text.strip()
    await update_channel_title(data['edit_ch_id'], new_title)
    await message.answer(f"✅ Kanal nomi muvaffaqiyatli <b>{new_title}</b> ga o'zgartirildi!", parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "back_to_ch_manage")
async def cb_back_to_ch_manage(callback: types.CallbackQuery):
    channels = await get_all_channels()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kanal qo'shish", callback_data="add_ch")
    builder.button(text="📝 Kanallar nomini tahrirlash", callback_data="list_edit_ch")
    builder.button(text="🗑 Kanallarni o'chirish", callback_data="list_del_ch")
    builder.adjust(1)
    
    msg = "📢 <b>Kanallar sozlamasi</b>\n\n"
    if not channels:
        msg += "Hozircha majburiy obuna kanallari yo'q."
    else:
        msg += "<b>Hozirgi kanallar:</b>\n"
        for ch in channels:
            msg += f"• {ch['title']} ({ch['channel_id']})\n"
            
    await callback.message.edit_text(msg, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "add_ch")
async def cb_add_channel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 <b>Kanal nomini kiriting:</b>\n(Masalan: 1 - kanal)", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_channel_title)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_channel_title)
async def process_ch_title(message: types.Message, state: FSMContext):
    if is_menu_button(message.text): 
        await state.clear()
        return
    await state.update_data(ch_title=message.text)
    await message.answer("🔗 <b>Kanal ID yoki Usernameni kiriting:</b>\n(Masalan: @channel_name yoki -100123456)")
    await state.set_state(AdminStates.waiting_for_channel_id)

@admin_router.message(AdminStates.waiting_for_channel_id)
async def process_ch_id(message: types.Message, state: FSMContext):
    if is_menu_button(message.text):
        await state.clear()
        return
    data = await state.get_data()
    ch_id = message.text.strip()
    url = f"https://t.me/{ch_id.strip('@')}" if not (ch_id.startswith('http') or ch_id.startswith('t.me')) else ch_id
    
    await add_channel(data['ch_title'], url, ch_id)
    await message.answer(f"✅ Kanal <b>{data['ch_title']}</b> muvaffaqiyatli qo'shildi!", parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data.startswith("del_ch:"))
async def cb_delete_channel(callback: types.CallbackQuery):
    ch_db_id = int(callback.data.split(":")[1])
    await delete_channel(ch_db_id)
    await callback.message.edit_text("✅ Kanal muvaffaqiyatli o'chirildi.")
    await callback.answer()
