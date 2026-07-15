# -*- coding: utf-8 -*-
"""Bot uchun barcha klaviaturalar (reply va inline)."""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import db


# ============================================================
# MIJOZ REPLY KLAVIATURALARI
# ============================================================
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🚖 Buyurtma berish")],
        [KeyboardButton(text="🧑\u200d✈️ Haydovchi bo'lish")],
        [KeyboardButton(text="📋 Buyurtmalarim")],
        [KeyboardButton(text="ℹ️ Yordam")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def category_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🏙 Shahar ichida")],
        [KeyboardButton(text="🛣 Viloyatlararo")],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


async def routes_keyboard(category: str) -> ReplyKeyboardMarkup:
    routes = await db.get_active_routes(category)
    rows = [[KeyboardButton(text=r[1])] for r in routes]
    rows.append([KeyboardButton(text="❌ Bekor qilish")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def count_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="1"), KeyboardButton(text="2")],
        [KeyboardButton(text="3"), KeyboardButton(text="4")],
        [KeyboardButton(text="📦 Pochta bor")],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def phone_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def location_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def pay_method_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="💵 Naqd pul")],
        [KeyboardButton(text="💳 Karta orqali")],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True
    )


# ============================================================
# HAYDOVCHI RO'YXATDAN O'TISH
# ============================================================
def driver_phone_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ============================================================
# BUYURTMA UCHUN INLINE TUGMALAR
# ============================================================
def order_admin_approve_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ord_ok:{order_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"ord_no:{order_id}"),
            ]
        ]
    )


def order_accept_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Men olaman", callback_data=f"acc:{order_id}")]
        ]
    )


def driver_request_admin_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"drv_ok:{req_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"drv_no:{req_id}"),
            ]
        ]
    )


# ============================================================
# ADMIN PANEL — INLINE MENYULAR
# ============================================================
def admin_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
            [InlineKeyboardButton(text="🧾 Kutilayotgan buyurtmalar", callback_data="adm:pending")],
            [InlineKeyboardButton(text="📜 So'nggi buyurtmalar", callback_data="adm:orders")],
            [InlineKeyboardButton(text="🗺 Yo'nalishlar / Narxlar", callback_data="adm:routes")],
            [InlineKeyboardButton(text="🚗 Haydovchilar", callback_data="adm:drivers")],
            [InlineKeyboardButton(text="🆕 Haydovchi so'rovlari", callback_data="adm:drv_requests")],
            [InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="adm:broadcast")],
            [InlineKeyboardButton(text="⚙️ Sozlamalar (guruhlar)", callback_data="adm:settings")],
        ]
    )


def back_button(target="adm:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data=target)]]
    )


def routes_category_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏙 Shahar ichida", callback_data="adm:routes_cat:city")],
            [InlineKeyboardButton(text="🛣 Viloyatlararo", callback_data="adm:routes_cat:intercity")],
            [InlineKeyboardButton(text="➕ Yangi yo'nalish qo'shish", callback_data="adm:route_add")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:home")],
        ]
    )


def route_detail_kb(route_id: int, active: bool, back_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=("🔕 O'chirish" if active else "🔔 Yoqish"),
                callback_data=f"adm:route_toggle:{route_id}:{back_to}",
            )],
            [InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"adm:route_price:{route_id}:{back_to}")],
            [InlineKeyboardButton(text="🗑 O'chirib tashlash", callback_data=f"adm:route_del:{route_id}:{back_to}")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"adm:routes_cat:{back_to}")],
        ]
    )


def driver_detail_kb(driver_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Ro'yxatdan chiqarish", callback_data=f"adm:driver_del:{driver_id}")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:drivers")],
        ]
    )


def settings_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏙 Shahar guruhini ID ni o'rnatish", callback_data="adm:set_group:city")],
            [InlineKeyboardButton(text="🛣 Viloyatlararo guruh ID ni o'rnatish", callback_data="adm:set_group:intercity")],
            [InlineKeyboardButton(text="💳 Karta raqamini o'rnatish", callback_data="adm:set_card")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:home")],
        ]
    )
