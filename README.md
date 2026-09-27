# 🎬 Telegram Subtitle Merger Bot

Telegram orqali videolarga subtitrlarni birlashtirib beruvchi va filmlarni yopiq kanalda keshlab saqlovchi professional bot.

---

## 🚀 Asosiy imkoniyatlar

1. **2 GB gacha fayllarni qo'llab-quvvatlash:**
   * Telethon (MTProto) orqali ishlaydi, standart 20 MB/50 MB limitlaridan ozod.
2. **Tezkor Soft-subtitr (Muxing):**
   * Video qayta kodlanmaydi (`-c copy`), 1 GB li film ham **20–30 soniyada** birlashtiriladi!
   * Eski Celeron/Pentium noutbuklarda ham hech qanday nagruzkasiz bemalol ishlaydi.
3. **Aqlli Kesh va Fayllar Ombori (Storage Channel):**
   * Tayyor bo'lgan har bir film yopiq Telegram kanaliga (`STORAGE_CHANNEL_ID`) yuklanadi va bazaga kiritiladi.
   * Agar boshqa foydalanuvchi xuddi shu filmni so'rasa, bot uni qayta ishlamaydi, 1 soniyada darhol forward qilib beradi!
4. **Hard-subtitr uchun tayyor poydevor:**
   * Hardcode (Videoga to'liq yopishtirish) bo'limi arxitekturaga kiritilgan, kelajakda kuchli serverga o'tilganda bir qatorda yoqilishi mumkin.
5. **Diskni avtomatik tozalash:**
   * Har bir yuklash va birlashtirishdan so'ng vaqtinchalik fayllar o'chiriladi, qattiq disk (HDD/SSD) to'lib qolmaydi.

---

## 📂 Loyiha tuzilmasi

```text
subtitle-bot/
├── bot.py             # Asosiy Telegram bot logikasi va eventlar
├── merger.py          # FFmpeg orqali subtitrni ulash mexanizmi
├── database.py        # SQLite ma'lumotlar bazasi va qidiruv tizimi
├── config.py          # Sozlamalar va muhit o'zgaruvchilari
├── requirements.txt   # Kerakli Python kutubxonalari
├── .env.example       # Konfiguratsiya namunasi
└── README.md          # Qo'llanma
```

---

## 🛠 O'rnatish va Ishga tushirish

### 1. Kerakli ma'lumotlarni olish
1. **BOT_TOKEN**: [@BotFather](https://t.me/BotFather) dan bot ochib token oling.
2. **API_ID va API_HASH**: [my.telegram.org](https://my.telegram.org) saytiga kirib, `API development tools` bo'limidan oling (1 GB+ fayllar bilan ishlash uchun kerak).
3. **STORAGE_CHANNEL_ID**: Telegramda bitta yopiq kanal (yoki guruh) oching, botni unga **Admin** qilib qo'shing va kanal ID sini oling (masalan: `-1001234567890`).

### 2. `.env` faylini sozlash
Loyihaning asosiy papkasida `.env` nomli fayl yarating (yoki `.env.example` dan nusxa oling) va ma'lumotlarni kiriting:

```env
BOT_TOKEN=1234567890:ABCdef...
API_ID=12345678
API_HASH=0123456789abcdef0123456789abcdef
STORAGE_CHANNEL_ID=-1001234567890
ADMIN_ID=123456789
```

---

### 3. Windows tizimida ishga tushirish

Terminalda (PowerShell yoki CMD):
```powershell
# Virtual muhitni faollashtirish
.venv\Scripts\activate

# Botni yurgazish
python bot.py
```

---

### 4. Eski noutbukda (Ubuntu Server) ishga tushirish

Ubuntu Server o'rnatilgan eski noutbukingizda:
```bash
# 1. Kerakli paketlarni o'rnatish
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git

# 2. Loyihani yuklash yoki ko'chirish
cd /home/ubuntu/
git clone <sizning-repo-link> subtitle-bot
cd subtitle-bot

# 3. Virtual muhit va kutubxonalar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. .env faylini yaratish
nano .env
# (Ma'lumotlarni yozib, Ctrl+O, Enter, Ctrl+X bosing)

# 5. Botni 24/7 fonda ishlashini ta'minlash (systemd xizmati)
sudo nano /etc/systemd/system/subtitle-bot.service
```

Xizmat fayli ichiga quyidagilarni yozing:
```ini
[Unit]
Description=Telegram Subtitle Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/subtitle-bot
ExecStart=/home/ubuntu/subtitle-bot/.venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Xizmatni yoqish:
```bash
sudo systemctl daemon-reload
sudo systemctl enable subtitle-bot
sudo systemctl start subtitle-bot
```

Botning holatini tekshirish:
```bash
sudo systemctl status subtitle-bot
```
