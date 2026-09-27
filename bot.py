import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeFilename

import config
import database
import merger

# Logging sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("SubtitleBot")

# Asosiy doimiy Reply menyu tugmalari
MAIN_KEYBOARD = [
    [Button.text("🔍 Kino qidirish", resize=True), Button.text("🔥 Yangi kinolar", resize=True)],
    [Button.text("ℹ️ Qo'llanma", resize=True), Button.text("❌ Bekor qilish", resize=True)]
]

# Telegram Client yaratish
client = None
if config.BOT_TOKEN and config.API_ID and config.API_HASH:
    client = TelegramClient(
        str(config.BASE_DIR / "bot_session"),
        api_id=config.API_ID,
        api_hash=config.API_HASH
    )
else:
    logger.warning("DIQQAT: .env faylida BOT_TOKEN, API_ID yoki API_HASH to'ldirilmagan!")
    client = TelegramClient(
        str(config.BASE_DIR / "bot_session"),
        api_id=123456,
        api_hash="0123456789abcdef0123456789abcdef"
    )

# Progress xabari uchun yordamchi
class ProgressTracker:
    def __init__(self, message, action_title="Yuklanmoqda"):
        self.message = message
        self.action_title = action_title
        self.last_update_time = 0
        self.last_percent = -1

    async def callback(self, current, total):
        if not total or total <= 0:
            return
        percent = int(current * 100 / total)
        current_time = time.time()
        # Birinchi marta darhol, keyin esa har 3 soniyada yoki har 5% da yangilash
        if (self.last_percent == -1 or current_time - self.last_update_time >= 3.0 or percent - self.last_percent >= 5) and percent != self.last_percent:
            self.last_update_time = current_time
            self.last_percent = percent
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            bar_len = 10
            filled = int(bar_len * percent / 100)
            bar = "▰" * filled + "▱" * (bar_len - filled)
            try:
                await self.message.edit(
                    f"⏳ **{self.action_title}...**\n"
                    f"`[{bar}]` {percent}%\n"
                    f"📊 {current_mb:.1f} MB / {total_mb:.1f} MB"
                )
            except Exception:
                pass


# Bir vaqtning o'zida ishlovchi videolar limiti (Peak time uchun xavfsizlik navbati)
MAX_CONCURRENT_TASKS = 2
task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
active_queue_count = 0
queue_lock = asyncio.Lock()


async def deliver_movie(event, movie: dict):
    """Kinoni foydalanuvchiga to'g'ridan-to'g'ri, toza ko'rinishda yuborish (Forward belgisiz)"""
    if not config.STORAGE_CHANNEL_ID:
        await event.respond("⚠️ Saqlash kanali sozlanmagan.")
        return

    try:
        chan_msg = await client.get_messages(config.STORAGE_CHANNEL_ID, ids=movie["channel_message_id"])
        size_mb = movie['file_size'] / (1024 * 1024) if movie.get('file_size') else 0
        caption = (
            f"🎬 **Film:** {movie['title']}\n"
            f"📦 **Hajmi:** {size_mb:.1f} MB\n"
            f"⚡ Soft-subtitr biriktirilgan\n\n"
            f"💡 *Maslahat: Subtitrni pleyer sozlamalaridan yoqishingiz mumkin (VLC yoki MX Player tavsiya etiladi).*"
        )
        if chan_msg and chan_msg.media:
            await client.send_file(
                event.chat_id,
                file=chan_msg.media,
                caption=caption
            )
        else:
            await client.forward_messages(
                entity=event.chat_id,
                messages=movie["channel_message_id"],
                from_peer=config.STORAGE_CHANNEL_ID
            )
    except Exception as e:
        logger.error(f"Kino yetkazishda xatolik: {e}")
        await event.respond(f"❌ Kinoni yetkazib berishda xatolik yuz berdi: {e}")


async def show_recent_movies(event):
    """Oxirgi qo'shilgan kinolar ro'yxati"""
    movies = database.get_recent_movies(limit=8)
    if not movies:
        await event.respond("📭 Hozircha bazada filmlar yo'q. Birinchi bo'lib video va subtitr yuborishingiz mumkin!", buttons=MAIN_KEYBOARD)
        return

    text = "🔥 **Oxirgi qo'shilgan filmlar:**\n\n"
    buttons = []
    for m in movies:
        size_mb = m['file_size'] / (1024 * 1024) if m['file_size'] else 0
        btn_text = f"▶️ {m['title']} ({size_mb:.1f} MB)" if size_mb > 0 else f"▶️ {m['title']}"
        buttons.append([Button.inline(btn_text, data=f"get_movie_{m['id']}")])

    await event.respond(text, buttons=buttons)


async def send_help_guide(event):
    """Foydalanish qo'llanmasi"""
    guide_text = (
        "📖 **Botdan foydalanish qo'llanmasi:**\n\n"
        "🎬 **1. Subtitrni videoga ulash:**\n"
        "1️⃣ Botga video yuboring (1–2 GB gacha).\n"
        "2️⃣ Unga mos `.srt`, `.vtt` subtitr faylini tashlang.\n"
        "3️⃣ Film nomini kiriting va **⚡ Subtitrni birlashtirish** tugmasini bosing!\n"
        "⏱ Jarayon 20–30 soniyada tayyor bo'ladi.\n\n"
        "🔍 **2. Kino qidirish:**\n"
        "• Shunchaki film nomini yozib yuboring (masalan: `Avatar`)\n\n"
        "💡 **Pleyerda subtitrni yoqish:**\n"
        "• **Telefonda:** VLC yoki MX Player orqali ochib, subtitr bo'limidan yoqing.\n"
        "• **Kompyuterda:** VLC Media Player, KMPlayer yoki PotPlayer orqali ko'ring."
    )
    await event.respond(guide_text, buttons=MAIN_KEYBOARD)


@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    if not event.is_private:
        return
    user_id = event.sender_id
    database.clear_user_session(user_id)
    total_count = database.get_total_movies_count()
    
    welcome_text = (
        "👋 **Assalomu alaykum!**\n\n"
        "Men videolarga subtitrlarni birlashtiruvchi va kino qidiruvchi botman.\n\n"
        "🎬 **Subtitr ulash uchun:**\n"
        "Menga to'g'ridan-to'g'ri **video fayl** yuboring (1–2 GB gacha).\n\n"
        "🔍 **Kino topish uchun:**\n"
        "Kino **nomini** (masalan: `Avatar`) yozib yuboring.\n\n"
        f"📊 Hozirda bazada: **{total_count} ta** film mavjud."
    )
    await event.respond(welcome_text, buttons=MAIN_KEYBOARD)


@client.on(events.NewMessage(pattern="/cancel"))
async def cancel_handler(event):
    if not event.is_private:
        return
    database.clear_user_session(event.sender_id)
    await event.respond("❌ Barcha jarayonlar bekor qilindi. Bosh menyudasiz.", buttons=MAIN_KEYBOARD)


@client.on(events.NewMessage(pattern="/recent"))
async def recent_command_handler(event):
    if not event.is_private:
        return
    await show_recent_movies(event)


@client.on(events.NewMessage(pattern="/help"))
async def help_command_handler(event):
    if not event.is_private:
        return
    await send_help_guide(event)


@client.on(events.NewMessage(func=lambda e: e.is_private and e.forward and (e.forward.chat or e.forward.channel_id)))
async def channel_detector_handler(event):
    """Faqat Admin uchun: kanaldan xabar forward qilinganda uning aniq ID sini chiqarib beradi va keshlaydi"""
    if config.ADMIN_ID and event.sender_id != config.ADMIN_ID:
        return

    chat_id = event.forward.chat_id
    title = getattr(event.forward.chat, "title", "Noma'lum kanal")
    
    try:
        await client.get_input_entity(chat_id)
    except Exception:
        pass

    await event.respond(
        f"📢 **Admin: Kanal ma'lumotlari aniqlandi!**\n\n"
        f"📛 Nomi: **{title}**\n"
        f"🆔 To'g'ri Kanal ID: `{chat_id}`\n\n"
        f"`.env` faylidagi `STORAGE_CHANNEL_ID` ga aynan shu `{chat_id}` ni yozing."
    )


@client.on(events.NewMessage(pattern=r"^/search(?:\s+(.+))?$"))
async def search_command_handler(event):
    if not event.is_private:
        return
    query = event.pattern_match.group(1)
    if not query:
        await event.respond("🔍 Qidirayotgan filmingiz nomini kiriting:\nMasalan: `/search Avatar`")
        return
    await perform_search(event, query)


async def perform_search(event, query: str):
    movies = database.search_movies(query, limit=6)
    if not movies:
        await event.respond(
            f"😔 Afsuski, **'{query}'** bo'yicha hech qanday film topilmadi.\n\n"
            f"💡 Nomni to'g'ri yozganingizga ishonch hosil qiling yoki yangi film qo'shish uchun video yuboring.",
            buttons=MAIN_KEYBOARD
        )
        return
    
    text = f"🎬 **'{query}' bo'yicha topilgan filmlar:**\n\n"
    buttons = []
    for m in movies:
        size_mb = m['file_size'] / (1024 * 1024) if m['file_size'] else 0
        btn_text = f"▶️ {m['title']} ({size_mb:.1f} MB)" if size_mb > 0 else f"▶️ {m['title']}"
        buttons.append([Button.inline(btn_text, data=f"get_movie_{m['id']}")])
    
    await event.respond(text, buttons=buttons)


@client.on(events.NewMessage(func=lambda e: e.is_private and (e.video or (e.document and e.file and e.file.mime_type and 'video' in e.file.mime_type))))
async def video_handler(event):
    user_id = event.sender_id
    
    file_name = "video.mp4"
    if event.file and event.file.name:
        file_name = event.file.name
    
    size_mb = (event.file.size / (1024 * 1024)) if (event.file and event.file.size) else 0

    database.update_user_session(
        user_id,
        state="WAITING_SUBTITLE",
        video_msg_id=event.id,
        video_name=file_name
    )

    cancel_btn = [[Button.inline("❌ Jarayonni bekor qilish", data="cancel_action")]]
    await event.respond(
        f"🎬 **1/3-qadam: Video qabul qilindi!**\n\n"
        f"📁 Nomi: `{file_name}`\n"
        f"📦 Hajmi: **{size_mb:.1f} MB**\n\n"
        f"Endi ushbu videoga mos **subtitr faylini** (`.srt`, `.vtt` yoki `.ass`) yuboring:",
        buttons=cancel_btn
    )


@client.on(events.NewMessage(func=lambda e: e.is_private and e.document and not (e.file and e.file.mime_type and 'video' in e.file.mime_type)))
async def document_handler(event):
    user_id = event.sender_id
    session = database.get_user_session(user_id)
    
    file_name = event.file.name.lower() if (event.file and event.file.name) else ""
    valid_exts = (".srt", ".vtt", ".ass", ".sub")
    is_subtitle = any(file_name.endswith(ext) for ext in valid_exts)
    
    if not is_subtitle:
        return

    if session.get("state") != "WAITING_SUBTITLE" or not session.get("video_msg_id"):
        await event.respond(
            "⚠️ Avval videoni yuboring, so'ngra uning subtitr faylini tashlang.\n"
            "Yoki boshlash uchun /start bosing.",
            buttons=MAIN_KEYBOARD
        )
        return

    database.update_user_session(
        user_id,
        state="WAITING_TITLE",
        subtitle_msg_id=event.id,
        subtitle_name=file_name
    )

    cancel_btn = [[Button.inline("❌ Jarayonni bekor qilish", data="cancel_action")]]
    await event.respond(
        f"📝 **2/3-qadam: Subtitr qabul qilindi!**\n\n"
        f"📄 Fayl: `{file_name}`\n\n"
        f"Endi ushbu film/videoning **nomini** (Title) yozib yuboring:\n"
        f"*(Masalan: `Qasoskorlar 1 (2012)`)*\n\n"
        f"⚠️ *Nom kiritilmasa, jarayon davom etmaydi.*",
        buttons=cancel_btn
    )


@client.on(events.NewMessage(func=lambda e: e.is_private and e.text and not e.text.startswith("/")))
async def text_handler(event):
    user_id = event.sender_id
    session = database.get_user_session(user_id)
    text = event.text.strip()

    # Reply menyu tugmalari bosilganda
    if text == "🔍 Kino qidirish":
        await event.respond(
            "🔍 Qidirayotgan filmingiz nomini yozib yuboring (masalan: `Avatar`):",
            buttons=MAIN_KEYBOARD
        )
        return

    if text == "🔥 Yangi kinolar":
        await show_recent_movies(event)
        return

    if text == "ℹ️ Qo'llanma":
        await send_help_guide(event)
        return

    if text == "❌ Bekor qilish":
        database.clear_user_session(user_id)
        await event.respond("❌ Barcha jarayonlar bekor qilindi.", buttons=MAIN_KEYBOARD)
        return

    # Agar foydalanuvchidan kino nomi kutilayotgan bo'lsa
    if session.get("state") == "WAITING_TITLE":
        existing = database.get_movie_by_title(text)
        database.update_user_session(user_id, state="CHOOSING_MODE", title=text)
        
        if existing:
            buttons = [
                [Button.inline("🎬 Darhol kinoni olish (1 soniya)", data=f"get_movie_{existing['id']}")],
                [Button.inline("⚡ Baribir qayta birlashtirish", data="mode_soft")],
                [Button.inline("❌ Bekor qilish", data="cancel_action")]
            ]
            await event.respond(
                f"💡 **Diqqat!**\n"
                f"`{text}` filmi bizning bazamizda **allaqachon mavjud**!\n"
                f"Kutib o'tirmasdan, uni darhol olishingiz mumkin:",
                buttons=buttons
            )
        else:
            buttons = [
                [Button.inline("⚡ Subtitrni birlashtirish (Soft - 20 soniya)", data="mode_soft")],
                [Button.inline("❌ Bekor qilish", data="cancel_action")]
            ]
            await event.respond(
                f"🎬 **3/3-qadam: Barchasi tayyor!**\n\n"
                f"Film nomi: **{text}**\n\n"
                f"Subtitrni ulash uchun quyidagi tugmani bosing:",
                buttons=buttons
            )
        return

    # Kino nomi bo'yicha qidiruv
    await perform_search(event, text)


@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    user_id = event.sender_id

    if data == "cancel_action":
        database.clear_user_session(user_id)
        await event.edit("❌ Jarayon bekor qilindi.")
        return

    if data.startswith("get_movie_"):
        movie_id = int(data.split("_")[2])
        movie = database.get_movie_by_id(movie_id)
        if not movie:
            await event.answer("Fayl topilmadi!", alert=True)
            return

        await event.answer("Kino yuborilmoqda...")
        await deliver_movie(event, movie)
        return

    if data == "mode_soft":
        global active_queue_count
        session = database.get_user_session(user_id)
        video_msg_id = session.get("video_msg_id")
        subtitle_msg_id = session.get("subtitle_msg_id")
        title = session.get("title") or "video"

        if not video_msg_id or not subtitle_msg_id:
            await event.edit("⚠️ Sessiya ma'lumotlari topilmadi. Qaytadan /start bosing.")
            return

        async with queue_lock:
            active_queue_count += 1
            queue_pos = active_queue_count

        if queue_pos > MAX_CONCURRENT_TASKS:
            waiting_ahead = queue_pos - MAX_CONCURRENT_TASKS
            approx_seconds = waiting_ahead * 30
            status_msg = await event.edit(
                f"⏳ **Siz navbatdasiz!**\n\n"
                f"⏱ Taxminiy kutish vaqti: **~{approx_seconds} soniya**.\n"
                f"Navbatingiz kelishi bilan jarayon avtomatik boshlanadi."
            )
        else:
            status_msg = await event.edit("⏳ **Jarayon boshlandi...**\nFayllar tekshirilmoqda...")

        # Vaqtinchalik fayl yo'llari
        task_id = f"{user_id}_{int(time.time())}"
        user_temp_dir = config.TEMP_DIR / task_id
        user_temp_dir.mkdir(parents=True, exist_ok=True)

        video_path = None
        sub_path = None
        output_path = user_temp_dir / f"{title}.mkv"

        try:
            async with task_semaphore:
                if queue_pos > MAX_CONCURRENT_TASKS:
                    await status_msg.edit("⏳ **Navbatingiz keldi! Jarayon boshlandi...**")

                # 1. Videoni yuklab olish (progress foizi bilan)
                video_msg = await client.get_messages(event.chat_id, ids=video_msg_id)
                tracker_down = ProgressTracker(status_msg, action_title="1/3 Video yuklab olinmoqda")
                video_path = await client.download_media(
                    video_msg,
                    file=user_temp_dir,
                    progress_callback=tracker_down.callback
                )

                # 2. Subtitrni yuklab olish
                await status_msg.edit("⏳ **2/3 Subtitr yuklab olinmoqda...**")
                sub_msg = await client.get_messages(event.chat_id, ids=subtitle_msg_id)
                sub_path = await client.download_media(sub_msg, file=user_temp_dir)

                # 3. Soft-subtitr biriktirish (FFmpeg)
                await status_msg.edit("⚙️ **3/3 Subtitr ulanmoqda (20 soniya)...**")
                success, msg = await merger.merge_soft_subtitles(
                    video_path=video_path,
                    subtitle_path=sub_path,
                    output_path=output_path
                )

                if not success:
                    await status_msg.edit(f"❌ Xatolik yuz berdi:\n`{msg}`")
                    return

                file_size = os.path.getsize(output_path)
                size_mb = file_size / (1024 * 1024)

                # 4. Storage kanali mavjudligini tekshirish
                chan_msg = None
                storage_available = False
                if config.STORAGE_CHANNEL_ID:
                    try:
                        await client.get_input_entity(config.STORAGE_CHANNEL_ID)
                        storage_available = True
                    except Exception:
                        storage_available = False

                new_movie_id = None
                if storage_available:
                    tracker_up = ProgressTracker(status_msg, action_title="🚀 Tayyor video yuborilmoqda")
                    chan_msg = await client.send_file(
                        config.STORAGE_CHANNEL_ID,
                        file=str(output_path),
                        caption=f"🎬 **Film:** {title}\n📦 **Hajmi:** {size_mb:.1f} MB",
                        part_size_kb=512,
                        progress_callback=tracker_up.callback
                    )
                    new_movie_id = database.add_movie(
                        title=title,
                        channel_message_id=chan_msg.id,
                        file_size=file_size,
                        uploader_id=user_id
                    )

                # 5. Foydalanuvchiga to'g'ridan-to'g'ri toza xabar qilib yetkazish (Forward belgisisiz!)
                await status_msg.edit("🎉 **Tayyor! Video sizga yetkazilmoqda...**")
                clean_caption = (
                    f"🎬 **Film:** {title}\n"
                    f"📦 **Hajmi:** {size_mb:.1f} MB\n"
                    f"⚡ Soft-subtitr muvaffaqiyatli biriktirildi!\n\n"
                    f"💡 *Maslahat: Subtitrni pleyer sozlamalaridan yoqishingiz mumkin (VLC yoki MX Player tavsiya etiladi).*"
                )

                if chan_msg and chan_msg.media:
                    await client.send_file(
                        event.chat_id,
                        file=chan_msg.media,
                        caption=clean_caption
                    )
                else:
                    tracker_user = ProgressTracker(status_msg, action_title="🚀 Tayyor video yuborilmoqda")
                    await client.send_file(
                        event.chat_id,
                        file=str(output_path),
                        caption=clean_caption,
                        part_size_kb=512,
                        progress_callback=tracker_user.callback
                    )

                await status_msg.delete()
                database.clear_user_session(user_id)

        except Exception as e:
            logger.exception("Jarayon davomida xatolik yuz berdi")
            await status_msg.edit(f"❌ Xatolik yuz berdi: {e}")
        finally:
            async with queue_lock:
                active_queue_count = max(0, active_queue_count - 1)
            try:
                import shutil
                if user_temp_dir.exists():
                    shutil.rmtree(user_temp_dir)
            except Exception as ex:
                logger.error(f"Temp fayllarni tozalashda xatolik: {ex}")


def main():
    database.init_db()
    logger.info("Baza ishga tushirildi.")
    
    if not config.BOT_TOKEN or not config.API_ID or not config.API_HASH:
        print("\n" + "=" * 60)
        print("XATOLIK: .env fayli sozlanmagan!")
        print("Iltimos, avval .env faylini yarating va BOT_TOKEN, API_ID,")
        print("API_HASH ma'lumotlarini kiriting.")
        print("Namuna uchun .env.example fayliga qarang.")
        print("=" * 60 + "\n")
        return

    while True:
        try:
            logger.info("Bot ishga tushmoqda...")
            client.start(bot_token=config.BOT_TOKEN)
            logger.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni kutmoqda!")
            client.run_until_disconnected()
        except (ConnectionError, OSError, Exception) as e:
            logger.warning(f"Internet yoki tarmoq uzildi ({e}). 5 soniyadan so'ng avtomatik qayta ulanadi...")
            time.sleep(5)


if __name__ == "__main__":
    main()
