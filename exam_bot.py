from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import random
import csv
import os
from flask import Flask
import threading

# ====== وب‌سرور کوچک برای Render ======
flask_app = Flask("")

@flask_app.route("/")
def home():
    return "Bot is running"

def run():
    flask_app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()
# ======================================

# شناسه ادمین
ADMIN_ID = 677533280

# فایل نتایج
RESULTS_FILE = "results.csv"
if not os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Student ID", "User ID", "Score", "Percent"])

# سوالات (نمونه)
QUESTIONS = [
    {"q": "پایتخت ایران کجاست؟", "options": ["مشهد", "تهران", "اصفهان", "تبریز"], "answer": 1},
    {"q": "عدد پی تقریباً چند است؟", "options": ["2.14", "3.14", "4.13", "2.71"], "answer": 1},
    {"q": "در کدام فصل بارش برف بیشتر است؟", "options": ["تابستان", "پاییز", "زمستان", "بهار"], "answer": 2},
    {"q": "نویسنده شاهنامه کیست؟", "options": ["سعدی", "مولوی", "فردوسی", "حافظ"], "answer": 2},
    {"q": "نخستین سیاره منظومه شمسی؟", "options": ["زهره", "عطارد", "مریخ", "زحل"], "answer": 1},
] * 6  # 30 سؤال

user_data = {}

# شروع آزمون
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in user_data and user_data[user_id].get("completed"):
        await update.message.reply_text("⚠️ شما قبلاً آزمون را انجام داده‌اید و مجاز به تکرار نیستید.")
        return

    user_data[user_id] = {"stage": "name"}
    await update.message.reply_text("👋 لطفاً نام و نام خانوادگی خود را وارد کنید:")

# دریافت نام و شماره دانشجویی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data:
        await update.message.reply_text("برای شروع آزمون دستور /start را بزنید.")
        return

    stage = user_data[user_id].get("stage")

    if stage == "name":
        user_data[user_id]["name"] = text
        user_data[user_id]["stage"] = "student_id"
        await update.message.reply_text("شماره دانشجویی خود را وارد کنید:")
    elif stage == "student_id":
        user_data[user_id]["student_id"] = text
        user_data[user_id]["stage"] = "exam"
        await update.message.reply_text("✅ اطلاعات ثبت شد.\nآزمون شروع می‌شود...")
        await start_exam(update, context)

# شروع آزمون
async def start_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    data["questions"] = random.sample(QUESTIONS, 30)
    data["index"] = 0
    data["score"] = 0
    data["completed"] = False
    await send_question(update, context)

# ارسال سؤال
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]

    if data["index"] >= len(data["questions"]):
        await finish_exam(update, context)
        return

    q = data["questions"][data["index"]]
    buttons = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(q["options"])]

    await update.message.reply_text(
        f"❓ سؤال {data['index'] + 1} از {len(data['questions'])}\n\n{q['q']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# پاسخ کاربر
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = user_data[user_id]
    q = data["questions"][data["index"]]
    answer = int(query.data)

    # نمره‌دهی
    if answer == q["answer"]:
        data["score"] += 1
    else:
        data["score"] -= 0.5  # نمره منفی

    data["index"] += 1

    if data["index"] < len(data["questions"]):
        await query.edit_message_text("✅ پاسخ ثبت شد! سؤال بعد:")
        # ارسال سؤال بعدی
        await send_next_question(context, user_id)
    else:
        await finish_exam(update, context)

# ارسال سؤال بعدی
async def send_next_question(context, user_id):
    class Dummy:
        def __init__(self, uid):
            self.effective_user = type('x', (), {'id': uid})
            self.message = type('y', (), {
                'reply_text': lambda *a, **kw: asyncio.create_task(
                    context.bot.send_message(chat_id=uid, **kw))
            })()
    await send_question(Dummy(user_id), context)

# پایان آزمون
async def finish_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    data["completed"] = True

    percent = max((data["score"] / len(data["questions"])) * 100, 0)
    name = data["name"]
    student_id = data["student_id"]

    # ذخیره در فایل CSV
    with open(RESULTS_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([name, student_id, user_id, data["score"], f"{percent:.1f}%"])

    # پیام به کاربر
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ آزمون تمام شد!\n📊 نمره شما: {data['score']} از {len(data['questions'])}\nدرصد پاسخ صحیح: {percent:.1f}%"
    )

    # پیام به ادمین
    msg = (
        f"📋 نتیجه آزمون جدید:\n\n"
        f"👤 نام: {name}\n"
        f"🎓 شماره دانشجویی: {student_id}\n"
        f"🆔 کاربر: {user_id}\n"
        f"📊 نمره: {data['score']} از {len(data['questions'])}\n"
        f"درصد: {percent:.1f}%"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
    except Exception as e:
        print("خطا در ارسال به ادمین:", e)

# ======== توکن ربات خود را اینجا قرار بده ========
TOKEN = "8475437543:AAG75xruJgLyAJnyD7WGsZlpsZu3dWs_ejE"

# اجرای ربات
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()









