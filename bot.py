import telebot
from telebot import types
import yfinance as yf
import pandas as pd
from flask import Flask
from threading import Thread

# 1. BOT SOZLAMALARI
TOKEN = '7943016839:AAEeCtXIWbDvTXz9fdsx8ok1Q3j-e8n3a1g'  # BotFather'dan olgan tokeningizni bering
bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is alive!"

def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. AQLLI TAHLIL FUNKSIYASI ---
def get_smart_signal(symbol, tf):
    try:
        # Ma'lumotni yuklash (biroz ko'proq ma'lumot olamiz)
        df = yf.download(symbol, period="5d", interval=tf, progress=False)
        if df.empty or len(df) < 30: return None

        # Indikatorlar
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain/loss)))

        last = df.iloc[-1]
        curr_p = float(last['Close'])
        rsi_v = float(last['RSI'])
        ema200 = float(last['EMA200'])

        # STRATEGIYA MANTIQI
        if curr_p > ema200:
            # Trend tepaga, lekin RSIga qaraymiz
            if rsi_v < 65: # Hali o'sishga joy bor
                action = "BOZORDAN KIRING (MARKET BUY) 🟢"
                entry_p = curr_p
            else: # RSI 65 dan baland - haddan tashqari qizigan, qaytishini kutamiz
                action = "LIMIT QO'YING (BUY LIMIT) ⏳"
                entry_p = ema200 * 1.0005 # EMAga yaqin joydan kutamiz
            sl = entry_p * 0.9980 # 0.2% Stop
            tp = entry_p * 1.0040 # 0.4% Profit
        else:
            # Trend pastga
            if rsi_v > 35: # Hali tushishga joy bor
                action = "BOZORDAN KIRING (MARKET SELL) 🔴"
                entry_p = curr_p
            else: # RSI 35 dan past - juda ko'p sotilgan, tepaga qaytishini kutamiz
                action = "LIMIT QO'YING (SELL LIMIT) ⏳"
                entry_p = ema200 * 0.9995
            sl = entry_p * 1.0020
            tp = entry_p * 0.9960

        return {
            "action": action, "entry": entry_p, "curr": curr_p,
            "sl": sl, "tp": tp, "rsi": rsi_v
        }
    except Exception as e:
        print(f"Xato: {e}")
        return None

# --- 3. TUGMALAR VA INTERFEYS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 Analizni Boshlash", "📈 Valyutalar Kuchi")
    markup.add("📅 Yangiliklar & Prognoz", "🧮 Risk Kalkulyatori")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 Professional Trading Terminal v2.0\nBot endi bozor holatini (Market/Limit) ajrata oladi.", 
                     reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 Analizni Boshlash")
def select_pair(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    pairs = {"🥇 Gold (XAUUSD)": "GC=F", "🇪🇺 EURUSD": "EURUSD=X", "🇬🇧 GBPUSD": "GBPUSD=X", "₿ Bitcoin": "BTC-USD"}
    for name, sym in pairs.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"p_{sym}"))
    bot.send_message(message.chat.id, "🎯 Juftlikni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
def select_tf(call):
    sym = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup(row_width=2)
    for tf in ["5m", "15m", "1h"]:
        markup.add(types.InlineKeyboardButton(tf, callback_data=f"a_{sym}_{tf}"))
    bot.edit_message_text(f"⏳ {sym} uchun vaqtni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("a_"))
def run_analysis(call):
    _, sym, tf = call.data.split('_')
    bot.answer_callback_query(call.id, "Tahlil qilinmoqda...")
    
    res = get_smart_signal(sym, tf)
    if res:
        msg = (
            f"🎯 {res['action']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 Aktiv: {sym} | {tf}\n"
            f"💵 Hozirgi narx: {res['curr']:.2f}\n"
            f"📍 Entry: {res['entry']:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🚫 SL: {res['sl']:.2f}\n"
            f"🎯 TP: {res['tp']:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 RSI: {res['rsi']:.2f}\n"
            f"💡 *Market bo'lsa - hozir kiring, Limit bo'lsa - Entry narxini kuting.*"
        )
    else:
        msg = "❌ Ma'lumot olishda xatolik."
    
    bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

# ... (Boshqa funksiyalar: News va Strength kodi shu yerda qoladi)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
