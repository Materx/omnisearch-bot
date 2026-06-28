#!/usr/bin/env python3
"""
OmniSearch Bot — Run on Render, Access from Any Device
"""

import requests
import json
import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XPON_URL = "https://api.xposedornot.com/v1"

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route("/")
def home():
    return "OmniSearch Bot is running!"

@app.route("/health")
def health():
    return "OK", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *OmniSearch Bot — Online 24/7*\n\n"
        "Send me any of these:\n\n"
        "\`--name John Smith --city Austin --state TX\`\n"
        "🔍 Finds addresses, relatives, background info\n\n"
        "\`--email target@example.com\`\n"
        "🔍 Checks if email was in data breaches\n\n"
        "\`--phone +14155551234\`\n"
        "🔍 Looks up phone number owner and location\n\n"
        "Works from any device — phone, laptop, PC, tablet!",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    await update.message.reply_text("🔍 Searching databases...")
    response_parts = []

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
                response_parts.append("⚠️ Whitepages key not set. Add WHITEPAGES_KEY in Render settings.\n")
        except Exception as e:
            response_parts.append(f"❌ Name error: {str(e)}\n")

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
                    l = data["location"]
                    result += f"📍 {l.get('city', '')}, {l.get('state', '')} {l.get('zip', '')}\n"
                if "line_type" in data:
                    result += f"📱 Type: {data['line_type']}\n"
                response_parts.append(result)
            else:
                response_parts.append(f"📞 *Phone: {phone}*\nℹ️ Add WHITEPAGES_KEY for details\n")
        except Exception as e:
            response_parts.append(f"❌ Phone error: {str(e)}\n")

    if not response_parts:
        response_parts.append(
            "⚠️ No valid search.\n\nTry:\n"
            "\`--email someone@example.com\`\n"
            "\`--name John Smith --city Austin --state TX\`\n"
            "\`--phone +14155551234\`"
        )
    full = "\n".join(response_parts)
    if len(full) > 4000:
        for i in range(0, len(full), 3900):
            await update.message.reply_text(full[i:i+3900], parse_mode="Markdown")
    else:
        await update.message.reply_text(full, parse_mode="Markdown")

def run_bot():
    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN not set!")
        return
    app_tg = Application.builder().token(TELEGRAM_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("🤖 OmniSearch Bot started!")
    app_tg.run_polling()

if __name__ == "__main__":
    bt = threading.Thread(target=run_bot, daemon=True)
    bt.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)