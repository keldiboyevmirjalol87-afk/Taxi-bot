# 🚕 Haydovchilar | TAXI — Telegram bot

To'liq ishlaydigan taxi-buyurtma boti: mijozlar uchun buyurtma oqimi, haydovchilar uchun
buyurtma qabul qilish, va adminlar uchun to'liq boshqaruv paneli.

## ⚠️ ENG MUHIM — XAVFSIZLIK

Agar avval sizning bot tokeningiz yoki guruh ID'ingiz biror joyda (chat, skrinshot va h.k.)
ochiq ko'rinib qolgan bo'lsa:

1. Telegram'da **@BotFather** ga o'ting
2. `/mybots` → botingizni tanlang → **API Token** → **Revoke current token**
3. Yangi tokenni oling va uni **faqat** `.env` fayliga yozing — hech qachon chatga, kodga
   yoki GitHub'ga ochiq yubormang

## 📁 Loyiha tuzilishi

```
taxibot/
├── bot.py              # Asosiy bot — mijoz oqimi, haydovchi buyurtma olishi
├── admin.py             # To'liq inline admin panel
├── db.py                 # SQLite bilan ishlash (barcha jadvallar)
├── keyboards.py           # Barcha reply/inline klaviaturalar
├── requirements.txt
├── .env.example           # Namuna sozlamalar fayli
└── README.md
```

## 🚀 O'rnatish

```bash
cd taxibot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example` faylini nusxalab `.env` deb nomlang, so'ng to'ldiring:

```bash
cp .env.example .env
```

`.env` ichida:
```
BOT_TOKEN=123456:AA...
ADMIN_IDS=111111111,222222222
```

- **BOT_TOKEN** — @BotFather'dan olingan token
- **ADMIN_IDS** — admin bo'ladigan Telegram user ID'lar, vergul bilan ajratilgan
  (ID ni bilish uchun @userinfobot'ga yozing)

Ishga tushirish:
```bash
python bot.py
```

## 🏙 Ikkita guruhni sozlash (shahar ichi / viloyatlararo)

1. Ikkita Telegram guruh yarating: masalan **"Haydovchilar — Shahar"** va
   **"Haydovchilar — Viloyatlararo"**
2. Botni har ikkala guruhga qo'shing va **admin** qiling
3. Har bir guruhda `/groupid` buyrug'ini yuboring — bot sizga o'sha guruhning chat ID'sini
   qaytaradi (manfiy raqam, masalan `-1001234567890`)
4. Botda `/admin` → **⚙️ Sozlamalar** → tegishli guruh turini tanlang → ID'ni yuboring

Shundan keyin admin buyurtmani tasdiqlaganda, u avtomatik ravishda tegishli guruhga
(shahar ichi yoki viloyatlararo) yuboriladi.

## 💳 To'lov (karta) sozlash

`/admin` → **⚙️ Sozlamalar** → **💳 Karta raqamini o'rnatish** → karta raqamini yuboring.

Mijoz "💳 Karta orqali" tanlasa, bot unga shu karta raqamini ko'rsatadi va to'lov chekini
(skrinshot) so'raydi. Chek admin panelga rasm bilan birga keladi.

## 🔄 To'liq oqim

### Mijoz tomonidan:
1. `/start` → asosiy menyu
2. **🚖 Buyurtma berish** → Shahar ichida / Viloyatlararo tanlanadi
3. Yo'nalish tanlanadi (narxi avtomatik ko'rsatiladi)
4. Yo'lovchi soni (1-4) yoki 📦 Pochta bor tanlanadi
5. Telefon raqam kiritiladi
6. Lokatsiya yuboriladi
7. To'lov usuli: 💵 Naqd yoki 💳 Karta (chek bilan)
8. Buyurtma **admin tasdig'ini kutish** holatiga o'tadi
9. Admin tasdiqlagach — mijozga xabar boradi, buyurtma guruhga va haydovchilarga yuboriladi

### Haydovchi tomonidan:
1. **🧑‍✈️ Haydovchi bo'lish** tugmasi bosiladi
2. Telefon raqam va mashina ma'lumoti kiritiladi
3. So'rov adminga ketadi
4. Admin tasdiqlasa — haydovchi faol haydovchilar ro'yxatiga qo'shiladi
5. Endi u yangi buyurtmalarni shaxsiy xabarda oladi va **"✅ Men olaman"** tugmasi orqali
   birinchi bo'lib bosgan haydovchi buyurtmani oladi (boshqalar uchun avtomatik yopiladi)

### Admin tomonidan (`/admin`):
- **📊 Statistika** — foydalanuvchilar soni, bugungi/jami buyurtmalar, tushum, top yo'nalishlar
- **🧾 Kutilayotgan buyurtmalar** — tasdiqlash/rad etish kerak bo'lganlar
- **📜 So'nggi buyurtmalar** — oxirgi 10 ta buyurtma holati bilan
- **🗺 Yo'nalishlar / Narxlar** — yo'nalish qo'shish, narxini o'zgartirish, yoqish/o'chirish, o'chirish
- **🚗 Haydovchilar** — faol haydovchilar ro'yxati va ularni o'chirish
- **🆕 Haydovchi so'rovlari** — yangi arizalarni tasdiqlash/rad etish
- **📢 Xabar tarqatish** — barcha foydalanuvchilarga bir vaqtda xabar yuborish
- **⚙️ Sozlamalar** — guruh ID'lari va karta raqamini o'rnatish

## 🗄 Baza

SQLite (`taxibot.db`) avtomatik yaratiladi, jadvallar: `routes`, `orders`, `drivers`,
`driver_requests`, `users`, `settings`. Boshqa serverga ko'chirsangiz shu faylni ko'chirish
kifoya (yoki serverda qaytadan bo'sh yaratiladi).

## ☁️ Doimiy ishlashi uchun (production)

Kompyuteringiz o'chganda bot ham to'xtaydi. Doimiy ishlashi uchun:
- VPS (masalan Timeweb, DigitalOcean) sotib olib, `systemd` service sifatida ishga tushiring, yoki
- Railway.app / Render.com kabi xizmatlarga deploy qiling

Kerak bo'lsa shu qadamni ham keyingi xabarda batafsil yozib beraman.
