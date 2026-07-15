# -*- coding: utf-8 -*-
"""
HAYDOVCHILAR | TAXI — to'liq Telegram bot

Funksiyalar:
- Mijoz: yo'nalish tanlash (shahar ichi / viloyatlararo) -> yo'lovchi soni yoki pochta
  -> telefon -> lokatsiya -> to'lov usuli (naqd / karta+chek) -> admin tasdiqlashini kutish
- Admin tasdiqlagach: buyurtma tegishli guruhga (shahar / viloyatlararo) va barcha faol
  haydovchilarga avtomatik yuboriladi
- Haydovchilar buyurtmani "✅ Men olaman" tugmasi orqali oladi (birinchi bosgan oladi)
- Haydovchi bo'lish: foydalanuvchi so'rov yuboradi -> admin tasdiqlaydi -> haydovchilar
  ro'yxatiga qo'shiladi
- To'liq inline admin panel (admin.py da): statistika, buyurtmalar, narxlar, haydovchilar,
  xabar tarqatish, guruh/karta sozlamalari

O'RNATISH:
    pip install aiogram aiosqlite python-dotenv

ISHGA TUSHIRISH:
    .env faylini to'ldiring (pastga qarang), so'ng:
    python bot.py

.env NAMUNASI (README.md da ham bor):
    BOT_TOKEN=123456:AA..."""

import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardRemove,
)

import db
import keyboards as kb
from admin import admin_router, is_admin

load_dotenv()


logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

router = Router()


# ============================================================
# FSM HOLATLAR
# ============================================================
class Order(StatesGroup):
    choosing_category = State()
    choosing_route = State()
    choosing_count = State()
    entering_phone = State()
    sending_location = State()
    choosing_pay_method = State()
    sending_pay_proof = State()


class DriverSignup(StatesGroup):
    entering_phone = State()
    entering_car = State()


# ============================================================
# /start va asosiy menyu
# ============================================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.upsert_user(
        message.from_user.id, message.from_user.full_name, message.from_user.username or ""
    )
    await message.answer(
        "🚕 <b>Haydovchilar | TAXI</b> ga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=kb.main_menu_keyboard(),
    )


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Bekor qilindi.", reply_markup=kb.main_menu_keyboard()
    )


@router.message(F.text == "ℹ️ Yordam")
async def help_msg(message: Message):
    await message.answer(
        "🚕 <b>Qanday foydalanish mumkin</b>\n\n"
        "• 🚖 Buyurtma berish — taksi chaqirish\n"
        "• 🧑\u200d✈️ Haydovchi bo'lish — haydovchi sifatida ro'yxatdan o'tish\n"
        "• 📋 Buyurtmalarim — oxirgi buyurtmalaringiz holati\n\n"
        "Savol bo'lsa admin bilan bog'laning."
    )


# ============================================================
# BUYURTMA BERISH — 1) Kategoriya (shahar / viloyatlararo)
# ============================================================
@router.message(F.text == "🚖 Buyurtma berish")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(Order.choosing_category)
    await message.answer(
        "🚖 Qaysi turdagi buyurtma kerak?",
        reply_markup=kb.category_keyboard(),
    )


@router.message(Order.choosing_category, F.text.in_(["🏙 Shahar ichida", "🛣 Viloyatlararo"]))
async def category_chosen(message: Message, state: FSMContext):
    category = "city" if message.text == "🏙 Shahar ichida" else "intercity"
    routes = await db.get_active_routes(category)
    if not routes:
        await message.answer(
            "Kechirasiz, hozircha bu toifada yo'nalishlar mavjud emas.",
            reply_markup=kb.main_menu_keyboard(),
        )
        await state.clear()
        return
    await state.update_data(category=category)
    await state.set_state(Order.choosing_route)
    await message.answer(
        "Bormoqchi bo'lgan yo'nalishingizni tanlang 👇",
        reply_markup=await kb.routes_keyboard(category),
    )


@router.message(Order.choosing_category)
async def category_invalid(message: Message):
    await message.answer("Iltimos, pastdagi tugmalardan tanlang 👇", reply_markup=kb.category_keyboard())


# ============================================================
# 2) Yo'nalish tanlash
# ============================================================
@router.message(Order.choosing_route)
async def route_chosen(message: Message, state: FSMContext):
    data = await state.get_data()
    routes = await db.get_active_routes(data.get("category"))
    match = next((r for r in routes if r[1] == message.text), None)
    if not match:
        await message.answer(
            "Iltimos, ro'yxatdan yo'nalishni tanlang 👇",
            reply_markup=await kb.routes_keyboard(data.get("category")),
        )
        return
    await state.update_data(route=match[1], price=match[2])
    await state.set_state(Order.choosing_count)
    await message.answer(
        "👥 Nechta yo'lovchi bor yoki 📦 pochta.",
        reply_markup=kb.count_keyboard(),
    )


# ============================================================
# 3) Yo'lovchi soni / Pochta
# ============================================================
@router.message(Order.choosing_count, F.text.in_(["1", "2", "3", "4"]))
async def count_chosen(message: Message, state: FSMContext):
    await state.update_data(passengers=message.text, is_cargo=False)
    await state.set_state(Order.entering_phone)
    await message.answer(
        "📞 Telefon raqamingizni yozing yoki pastdagi 📱 tugma orqali yuboring:\n\n+998",
        reply_markup=kb.phone_keyboard(),
    )


@router.message(Order.choosing_count, F.text == "📦 Pochta bor")
async def cargo_chosen(message: Message, state: FSMContext):
    await state.update_data(passengers=None, is_cargo=True)
    await state.set_state(Order.entering_phone)
    await message.answer(
        "📞 Telefon raqamingizni yozing yoki pastdagi 📱 tugma orqali yuboring:\n\n+998",
        reply_markup=kb.phone_keyboard(),
    )


@router.message(Order.choosing_count)
async def count_invalid(message: Message):
    await message.answer(
        "Iltimos, 1-4 orasidan tanlang yoki 📦 Pochta bor tugmasini bosing.",
        reply_markup=kb.count_keyboard(),
    )


# ============================================================
# 4) Telefon raqam
# ============================================================
@router.message(Order.entering_phone, F.contact)
async def phone_from_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await ask_location(message, state)


@router.message(Order.entering_phone, F.text)
async def phone_from_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    numbers_only = "".join(ch for ch in digits if ch.isdigit())
    if len(numbers_only) < 9:
        await message.answer(
            "Raqam noto'g'ri ko'rinmoqda. Qaytadan kiriting, masalan: +998901234567",
            reply_markup=kb.phone_keyboard(),
        )
        return
    await state.update_data(phone=digits)
    await ask_location(message, state)


async def ask_location(message: Message, state: FSMContext):
    await state.set_state(Order.sending_location)
    await message.answer(
        "📍 Bormoqchi bo'lgan joyingizni belgilang (lokatsiya yuboring).",
        reply_markup=kb.location_keyboard(),
    )


# ============================================================
# 5) Lokatsiya -> To'lov usuli so'raladi
# ============================================================
@router.message(Order.sending_location, F.location)
async def location_received(message: Message, state: FSMContext):
    await state.update_data(
        lat=message.location.latitude, lon=message.location.longitude
    )
    await state.set_state(Order.choosing_pay_method)
    await message.answer(
        "💳 To'lov usulini tanlang:",
        reply_markup=kb.pay_method_keyboard(),
    )


@router.message(Order.sending_location)
async def location_invalid(message: Message):
    await message.answer(
        "Iltimos, 📍 tugma orqali lokatsiyangizni yuboring.",
        reply_markup=kb.location_keyboard(),
    )


# ============================================================
# 6) To'lov usuli
# ============================================================
@router.message(Order.choosing_pay_method, F.text == "💵 Naqd pul")
async def pay_cash(message: Message, state: FSMContext):
    await state.update_data(pay_method="naqd", pay_proof_file_id=None)
    await finalize_order(message, state)


@router.message(Order.choosing_pay_method, F.text == "💳 Karta orqali")
async def pay_card(message: Message, state: FSMContext):
    card_number = await db.get_setting("card_number", "Karta raqami hali admin tomonidan kiritilmagan")
    await state.update_data(pay_method="karta")
    await state.set_state(Order.sending_pay_proof)
    await message.answer(
        f"💳 To'lov uchun karta raqami:\n\n<code>{card_number}</code>\n\n"
        f"To'lovni amalga oshirib, chek yoki skrinshot rasmini shu yerga yuboring.",
        reply_markup=kb.cancel_keyboard(),
    )


@router.message(Order.choosing_pay_method)
async def pay_method_invalid(message: Message):
    await message.answer("Iltimos, pastdagi tugmalardan tanlang 👇", reply_markup=kb.pay_method_keyboard())


@router.message(Order.sending_pay_proof, F.photo)
async def pay_proof_received(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(pay_proof_file_id=file_id)
    await finalize_order(message, state)


@router.message(Order.sending_pay_proof)
async def pay_proof_invalid(message: Message):
    await message.answer("Iltimos, to'lov chekini rasm shaklida yuboring.")


# ============================================================
# BUYURTMANI YAKUNLASH — admin tasdiqlashini kutish holatiga o'tadi
# ============================================================
async def finalize_order(message: Message, state: FSMContext):
    from admin import ADMIN_IDS
    from aiogram import Bot

    data = await state.get_data()
    bot: Bot = message.bot

    order_id = await db.create_order(
        {
            "user_id": message.from_user.id,
            "full_name": message.from_user.full_name,
            "username": message.from_user.username or "",
            "route": data.get("route"),
            "category": data.get("category"),
            "price": data.get("price", 0),
            "passengers": data.get("passengers"),
            "is_cargo": data.get("is_cargo", False),
            "phone": data.get("phone"),
            "lat": data.get("lat"),
            "lon": data.get("lon"),
            "pay_method": data.get("pay_method"),
            "pay_proof_file_id": data.get("pay_proof_file_id"),
        }
    )

    await message.answer(
        "✅ Buyurtmangiz qabul qilindi va admin tasdig'ini kutmoqda.\n"
        "Tasdiqlangach sizga xabar beramiz!",
        reply_markup=kb.main_menu_keyboard(),
    )

    who = "📦 Pochta" if data.get("is_cargo") else f"👥 Yo'lovchilar: {data.get('passengers')}"
    price = data.get("price", 0)
    price_str = f"{price:,}".replace(",", " ") if price else "0"
    cat_title = "🏙 Shahar ichida" if data.get("category") == "city" else "🛣 Viloyatlararo"

    admin_text = (
        f"🆕 <b>Yangi buyurtma #{order_id}</b> (tasdiq kutmoqda)\n\n"
        f"{cat_title}\n"
        f"🚖 Yo'nalish: {data.get('route')}\n"
        f"{who}\n"
        f"💰 Narx: {price_str} so'm\n"
        f"💳 To'lov: {data.get('pay_method')}\n"
        f"📞 Telefon: {data.get('phone')}\n"
        f"👤 Mijoz: {message.from_user.full_name} (@{message.from_user.username or 'yoq'})\n"
        f"🕒 Vaqt: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
    )

    for admin_id in ADMIN_IDS:
        try:
            if data.get("pay_proof_file_id"):
                await bot.send_photo(
                    admin_id,
                    data["pay_proof_file_id"],
                    caption=admin_text,
                    reply_markup=kb.order_admin_approve_kb(order_id),
                )
            else:
                await bot.send_message(
                    admin_id, admin_text, reply_markup=kb.order_admin_approve_kb(order_id)
                )
        except Exception as e:
            logging.warning(f"Adminga yuborishda xatolik: {e}")

    await state.clear()


# ============================================================
# HAYDOVCHI BUYURTMANI OLADI ("✅ Men olaman")
# ============================================================
@router.callback_query(F.data.startswith("acc:"))
async def order_accepted(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    status = order[14]
    user_id = order[1]

    if status == "accepted":
        await callback.answer("Bu buyurtmani boshqa haydovchi allaqachon oldi.", show_alert=True)
        return
    if status != "approved":
        await callback.answer("Bu buyurtma hali admin tomonidan tasdiqlanmagan.", show_alert=True)
        return

    await db.set_order_status(order_id, "accepted", callback.from_user.id)

    try:
        if callback.message.text:
            await callback.message.edit_text(
                callback.message.text + f"\n\n✅ Oldi: {callback.from_user.full_name}"
            )
        else:
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + f"\n\n✅ Oldi: {callback.from_user.full_name}"
            )
    except Exception:
        pass

    await callback.answer("Buyurtma sizga biriktirildi ✅")

    try:
        await bot.send_message(
            user_id,
            f"🚕 Haydovchi topildi!\n👤 {callback.from_user.full_name}\n"
            f"📞 Tez orada siz bilan bog'lanadi.",
        )
    except Exception:
        pass


# ============================================================
# HAYDOVCHI BO'LISH — so'rov yuborish
# ============================================================
@router.message(F.text == "🧑\u200d✈️ Haydovchi bo'lish")
async def driver_signup_start(message: Message, state: FSMContext):
    drivers = await db.get_active_driver_ids()
    if message.from_user.id in drivers:
        await message.answer("Siz allaqachon haydovchi sifatida ro'yxatdan o'tgansiz ✅")
        return
    await state.set_state(DriverSignup.entering_phone)
    await message.answer(
        "🧑\u200d✈️ Haydovchi bo'lish uchun ariza.\n\n"
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=kb.driver_phone_keyboard(),
    )


@router.message(DriverSignup.entering_phone, F.contact)
async def driver_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await ask_driver_car(message, state)


@router.message(DriverSignup.entering_phone, F.text)
async def driver_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if len("".join(ch for ch in digits if ch.isdigit())) < 9:
        await message.answer("Raqam noto'g'ri ko'rinmoqda. Qaytadan kiriting.")
        return
    await state.update_data(phone=digits)
    await ask_driver_car(message, state)


async def ask_driver_car(message: Message, state: FSMContext):
    await state.set_state(DriverSignup.entering_car)
    await message.answer(
        "🚘 Mashinangiz haqida yozing (marka, model, davlat raqami).\nMasalan: Chevrolet Cobalt, 01 A 123 BC",
        reply_markup=kb.cancel_keyboard(),
    )


@router.message(DriverSignup.entering_car)
async def driver_car_received(message: Message, state: FSMContext, bot: Bot):
    from admin import ADMIN_IDS

    data = await state.get_data()
    req_id = await db.create_driver_request(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username or "",
        data.get("phone"),
        message.text,
    )
    await state.clear()
    await message.answer(
        "✅ Arizangiz qabul qilindi va admin tasdig'ini kutmoqda.",
        reply_markup=kb.main_menu_keyboard(),
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🧑\u200d✈️ <b>Yangi haydovchi so'rovi</b>\n\n"
                f"👤 {message.from_user.full_name}\n"
                f"📞 {data.get('phone')}\n"
                f"🚘 {message.text}",
                reply_markup=kb.driver_request_admin_kb(req_id),
            )
        except Exception:
            pass


# ============================================================
# BUYURTMALARIM
# ============================================================
@router.message(F.text == "📋 Buyurtmalarim")
async def my_orders(message: Message):
    async with __import__("aiosqlite").connect(db.DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT id, route, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5",
            (message.from_user.id,),
        )
        orders = await cur.fetchall()

    if not orders:
        await message.answer("Sizda hali buyurtmalar yo'q.")
        return

    status_map = {
        "pending_admin": "⏳ Tasdiqlanmoqda",
        "approved": "✅ Tasdiqlangan, haydovchi kutilmoqda",
        "rejected": "❌ Rad etilgan",
        "accepted": "🚗 Haydovchi topildi",
    }
    lines = ["📋 <b>So'nggi buyurtmalaringiz</b>\n"]
    for oid, route, status, created in orders:
        time_str = created.split("T")[0]
        lines.append(f"#{oid} — {status_map.get(status, status)}\n{route}\n🕒 {time_str}")
    await message.answer("\n\n".join(lines))


# ============================================================
# Boshqa har qanday xabar
# ============================================================
@router.message()
async def fallback(message: Message):
    await message.answer("Menyudan birini tanlang 👇", reply_markup=kb.main_menu_keyboard())


# ============================================================
async def main():
    if not BOT_TOKEN:
        print("\n❌ XATO: .env faylida BOT_TOKEN topilmadi. README.md ga qarang.\n")
        return

    await db.init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(router)

    print("================================")
    print("🚕 TAXI BOT ISHGA TUSHDI!")
    print("================================")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
