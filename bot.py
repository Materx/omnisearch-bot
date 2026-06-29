#!/usr/bin/env python3
"""
OmniSearch Bot — Interactive Menu Version
"""

import requests
import json
import os
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XPON_URL = "https://api.xposedornot.com/v1"

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "OmniSearch Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

# ============================
# MENU SYSTEM
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Search by Name", callback_data="menu_name")],
        [InlineKeyboardButton("📧 Search by Email", callback_data="menu_email")],
        [InlineKeyboardButton("📞 Search by Phone", callback_data="menu_phone")],
        [InlineKeyboardButton("❓ Help", callback_data="menu_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *OmniSearch Bot*\n\n"
        "What would you like to search?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_name":
        await query.edit_message_text(
            "📋 *Name Search*\n\n"
            "Send me a message like this:\n\n"
            "`--name John Smith --city Austin --state TX`\n\n"
            "City and state are optional. Just `--name John Smith` works too.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]
            ])
        )
    
    elif query.data == "menu_email":
        await query.edit_message_text(
            "📧 *Email Search*\n\n"
            "Send me a message like this:\n\n"
            "`--email target@example.com`\n\n"
            "I'll check if that email appears in known data breaches.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]
            ])
        )
    
    elif query.data == "menu_phone":
        await query.edit_message_text(
            "📞 *Phone Search*\n\n"
            "Send me a message like this:\n\n"
            "`--phone +14155551234`\n\n"
            "Include the country code (+1 for US).",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]
            ])
        )
    
    elif query.data == "menu_help":
        await query.edit_message_text(
            "❓ *Help*\n\n"
            "I search public databases for information.\n\n"
            "• **Name** — finds addresses, age, relatives\n"
            "• **Email** — checks data breach history\n"
            "• **Phone** — finds carrier, location\n\n"
            "Results are based on publicly available data.\n"
            "Some features require API keys to be configured.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]
            ])
        )
    
    elif query.data == "menu_back":
        keyboard = [
            [InlineKeyboardButton("🔍 Search by Name", callback_data="menu_name")],
            [InlineKeyboardButton("📧 Search by Email", callback_data="menu_email")],
            [InlineKeyboardButton("📞 Search by Phone", callback_data="menu_phone")],
            [InlineKeyboardButton("❓ Help", callback_data="menu_help")],
        ]
        await query.edit_message_text(
            "🤖 *OmniSearch Bot*\n\n"
            "What would you like to search?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ============================
# SEARCH HANDLER
# ============================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    
    # If user types /start, show menu
    if msg.lower() == "/start":
        await start(update, context)
        return
    
    # If message doesn't have --name, --email, or --phone, show error with menu
    if "--name" not in msg and "--email" not in msg and "--phone" not in msg:
        keyboard = [
            [InlineKeyboardButton("🔍 Search by Name", callback_data="menu_name")],
            [InlineKeyboardButton("📧 Search by Email", callback_data="menu_email")],
            [InlineKeyboardButton("📞 Search by Phone", callback_data="menu_phone")],
        ]
        await update.message.reply_text(
            "⚠️ I didn't understand that.\n\n"
            "Use the buttons below or send:\n"
            "`--name John Smith --city Austin`\n"
            "`--email test@example.com`\n"
            "`--phone +14155551234`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    await update.message.reply_text("🔍 Searching databases...")
    response_parts = []

    # --- NAME SEARCH ---
    if "--name" in msg:
        try:
            parts = msg.split("--name")[1].strip().split("--")
            name = parts[0].strip()
            city = None
            state = None
            for p in parts[1:]:
                if p.startswith("city"):
                    city = p.split("city")[1].strip()
                if p.startswith("state"):
                    state = p.split("state")[1].strip()
            wp_key = os.environ.get("WHITEPAGES_KEY", "")
            if wp_key:
                url = "https://proapi.whitepages.com/3.0/person"
                params = {"api_key": wp_key, "name": name}
                if city: params["city"] = city
                if state: params["state"] = state
                r = requests.get(url, params=params, timeout=15)
                data = r.json()
                result = f"📋 *Name Search: {name}*\n"
                if "results" in data and data["results"]:
                    for person in data["results"][:3]:
                        n = person.get("names", [{}])
                        loc = person.get("locations", [{}])
                        age = person.get("age_range", {})
                        fn = n[0].get("display", "Unknown") if n else "Unknown"
                        ll = f"{loc[0].get('city', '')}, {loc[0].get('state_code', '')}" if loc else "Unknown"
                        a = f"{age.get('start', '')}-{age.get('end', '')}" if age else "Unknown"
                        result += f"\n👤 *{fn}*\n📍 {ll}\n📅 Age: {a}\n"
                else:
                    result += "No results found\n"
                response_parts.append(result)
            else:
                response_parts.append("⚠️ Whitepages API key not configured. Name search unavailable.\n")
        except Exception as e:
            response_parts.append(f"❌ Name error: {str(e)}\n")

    # --- EMAIL SEARCH ---
    if "--email" in msg:
        try:
            email = msg.split("--email")[1].strip().split()[0]
            r = requests.get(f"{XPON_URL}/email/{email}", timeout=15)
            data = r.json()
            result = f"📧 *Email Search: {email}*\n"
            breaches = data.get("breaches", data.get("result", []))
            if breaches:
                result += f"⚠️ Found in {len(breaches)} breach(es):\n"
                for b in breaches[:10]:
                    result += f"• {b.get('name', b.get('Title', 'Unknown'))}\n"
            else:
                result += "✅ No breaches found\n"
            response_parts.append(result)
        except Exception as e:
            response_parts.append(f"❌ Email error: {str(e)}\n")

    # --- PHONE SEARCH ---
    if "--phone" in msg:
        try:
            phone = msg.split("--phone")[1].strip().split()[0]
            wp_key = os.environ.get("WHITEPAGES_KEY", "")
            if wp_key:
                r = requests.get("https://proapi.whitepages.com/3.0/phone",
                    params={"api_key": wp_key, "phone": phone}, timeout=15)
                data = r.json()
                result = f"📞 *Phone: {phone}*\n"
                if "carrier" in data:
                    result += f"🏢 Carrier: {data['carrier']}\n"
                if "location" in data:
                    l = data['location']
                    result += f"📍 {l.get('city', '')}, {l.get('state', '')} {l.get('zip', '')}\n"
                if "line_type" in data:
                    result += f"📱 Type: {data['line_type']}\n"
                response_parts.append(result)
            else:
                response_parts.append(f"📞 *Phone: {phone}*\nℹ️ Add WHITEPAGES_KEY for phone details\n")
        except Exception as e:
            response_parts.append(f"❌ Phone error: {str(e)}\n")

    full = "\n".join(response_parts)
    
    # Add menu button at the end
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
    
    if len(full) > 4000:
        for i in range(0, len(full), 3900):
            if i == 0:
                await update.message.reply_text(full[i:i+3900], parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(full[i:i+3900], parse_mode="Markdown")
    else:
        await update.message.reply_text(full, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def run_bot():
    if not TELEGRAM_TOKEN:
        logging.error("TELEGRAM_TOKEN not set!")
        return
    app_tg = Application.builder().token(TELEGRAM_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CallbackQueryHandler(button_handler))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("OmniSearch Bot started!")
    app_tg.run_polling()

if __name__ == "__main__":
    bt = threading.Thread(target=run_bot, daemon=True)
    bt.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)