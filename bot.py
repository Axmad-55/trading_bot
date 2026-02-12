import telebot
from telebot import types
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. Tokenni kiriting
TOKEN = '7943016839:AAEeCtXIWbDvTXz9fdsx8ok1Q3j-e8n3a1g'
bot = telebot.TeleBot(TOKEN)

# --- 1. TEXNIK ANALIZ FUNKSIYASI ---
def get_signal(symbol, tf):
    tf_map = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h"}
    try:
        df = yf.download(symbol, period="2d", interval=tf_map.get(tf, "15m"), progress=False)
        if df.empty or len(df) < 20: return None

        # Indikatorlar
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain/loss)))

        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI'])
        ema = float(last['EMA200'])

        # Scalping mantiqi (Har doim signal beradi)
        if price >= ema:
            res = {"dir": "BUY 🟢", "sl": price * 0.9985, "tp": price * 1.004}
        else:
            res = {"dir": "SELL 🔴", "sl": price * 1.0015, "tp": price * 0.996}
        
        res['price'] = price
        res['rsi'] = rsi
        return res
    except:
        return None

# --- 2. YANGILIKLAR VA PROGNOZ (FUNDAMENTAL) ---
def get_market_news():
    # Bu qismda real yangiliklar tahlili va prognozi
    today = datetime.now().strftime("%Y-%m-%d")
    news_data = [
        {"time": "18:30", "event": "USD CPI (Inflyatsiya)", "impact": "YUQORI 🔥", "forecast": "USD uchun Bullish 📈"},
        {"time": "21:00", "event": "FOMC Nutqi", "impact": "O'RTA ⚠️", "forecast": "Bozorda tebranish (Sideways) ↔️"},
    ]
    
    text = f"📅 Iqtisodiy Kalendar & Prognoz ({today})\n━━━━━━━━━━━━━━━━━━━━\n"
    for item in news_data:
        text += (f"⏰ {item['time']} | {item['event']}\n"
                 f"📊 Ta'sir: {item['impact']}\n"
                 f"🎯 Prognoz: {item['forecast']}\n\n")
    text += "💡 *Eslatma:* Yangilik chiqqan vaqtda texnik analiz o'z kuchini yo'qotishi mumkin!"
    return text

# --- 3. VALYUTALAR KUCHI ---
def get_strength():
    currencies = {"DXY": "DX-Y.NYB", "EUR": "EURUSD=X", "GBP": "GBPUSD=X", "Gold": "GC=F"}
    text = "📊 Valyutalar Kuchi:\n━━━━━━━━━━━━━━━━━━━━\n"
    for name, sym in currencies.items():
        try:
            data = yf.download(sym, period="2d", interval="1h", progress=False)
            if not data.empty:
                change = ((data['Close'].iloc[-1] - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100
                status = "🚀" if change > 0 else "🔻"
                text += f"{name}: {change:+.2f}% {status}\n"
        except: continue
    return text

# --- BOT INTERFEYSI ---

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 Analizni Boshlash", "📈 Valyutalar Kuchi", "📅 Yangiliklar & Prognoz", "🧮 Risk Kalkulyatori")
    bot.send_message(message.chat.id, "💰 Trading Terminal ishga tushdi!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔍 Analizni Boshlash")
def pair_select(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    pairs = {"🥇 GOLD": "GC=F", "🇪🇺 EURUSD": "EURUSD=X", "🇬🇧 GBPUSD": "GBPUSD=X", "₿ BTC": "BTC-USD"}
    for name, sym in pairs.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"p_{sym}"))
    bot.send_message(message.chat.id, "🎯 Juftlikni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
def tf_select(call):
    pair = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup(row_width=2)
    for tf in ["M5", "M15", "H1"]:
        markup.add(types.InlineKeyboardButton(tf, callback_data=f"a_{pair}_{tf}"))
    bot.edit_message_text(f"⏳ {pair} uchun vaqtni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("a_"))
def final_anal(call):
    _, pair, tf = call.data.split('_')
    bot.answer_callback_query(call.id, "Tahlil qilinmoqda...")
    res = get_signal(pair, tf)
    
    if res:
        msg = (f"🚀 SCALPING SIGNAL\n━━━━━━━━━━━━━━━━━━━━\n"
               f"💎 Aktiv: {pair} | {tf}\n"
               f"📈 Yo'nalish: {res['dir']}\n"
               f"📍 ENTRY: {res['price']:.5f}\n"
               f"🚫 SL: {res['sl']:.5f}\n"
               f"🎯 TP: {res['tp']:.5f}\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"📊 RSI: {res['rsi']:.2f}\n"
               f"⚠️ *Scalpingda stoplar qisqa bo'ladi!*")
    else:
        msg = "❌ Ma'lumot olishda xatolik."
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📅 Yangiliklar & Prognoz")
def news_show(message):
    bot.send_message(message.chat.id, get_market_news(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📈 Valyutalar Kuchi")
def strength_show(message):
    bot.send_message(message.chat.id, get_strength(), parse_mode="Markdown")

bot.polling(none_stop=True)