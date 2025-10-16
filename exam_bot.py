from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import csv
import os
from flask import Flask
import threading

# ===== وب سرور کوچک برای Render Web Service =====
flask_app = Flask("")

@flask_app.route("/")
def home():
    return "Bot is running"

def run():
    flask_app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()
# ===============================================

# فایل نتایج
RESULTS_FILE = "results.csv"

if not os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Name", "Score", "Percent", "Answers"])

# سوالات آزمایشی (30 سوال)
QUESTIONS = [
    {"q": "پایتخت ایران کجاست؟", "options": ["مشهد", "تهران", "اصفهان", "تبریز"], "answer": 1},
    {"q": "عدد پی تقریباً چند است؟", "options": ["2.14", "3.14", "4.13", "2.71"], "answer": 1},
    {"q": "در کدام فصل بارش برف بیشتر است؟", "options": ["تابستان", "پاییز", "زمستان", "بهار"], "answer": 2},
    {"q": "نویسنده شاهنامه کیست؟", "options": ["سعدی", "مولوی", "فردوسی", "حافظ"], "answer": 2},
    {"q": "نخستین سیاره منظومه شمسی؟", "options": ["زهره", "عطارد", "مریخ", "زحل"], "answer": 1},
    {"q": "حاصل ۵×۶ چیست؟", "options": ["۳۰", "۲۶", "۳۶", "۳۲"], "answer": 0},
    {"q": "در کدام کشور برج ایفل قرار دارد؟", "options": ["فرانسه", "ایتالیا", "آلمان", "انگلستان"], "answer": 0},
    {"q": "نویسنده گلستان؟", "options": ["سعدی", "حافظ", "فردوسی", "خیام"], "answer": 0},
    {"q": "آب در چند درجه یخ می‌زند؟", "options": ["۰", "۱۰۰", "۵۰", "۲۵"], "answer": 0},
    {"q": "بزرگ‌ترین قاره جهان؟", "options": ["اروپا", "آسیا", "آفریقا", "آمریکا"], "answer": 1},
] * 3  # 30 سوال

# اطلاعات کاربران
user_data = {}

# فرمان /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if user_id in user_data and user_data[user_id].get("completed"):
        await update.message.reply_text("⚠️ شما قبلاً آزمون را انجام داده‌اید و مجاز به تکرار نیستید.")
        return

    random_questions = random.sample(QUESTIONS, 30)
    user_data[user_id] = {
        "name": name,
        "questions": random_questions,
        "index": 0,
        "score": 0,
        "answers": [],
        "completed": False
    }

    await send_question(update, context)

# ارسال سوال بعدی
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]

    if data["index"] < len(data["questions"]):
        q = data["questions"][data["index"]]
        buttons = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(q["options"])]
        await update.message.reply_text(
            f"سؤال {data['index'] + 1} از {len(data['questions'])}:\n\n{q['q']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await finish_exam(update, context)

# مدیریت پاسخ دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_data[user_id]
    q = data["questions"][data["index"]]
    answer = int(query.data)

    correct = (answer == q["answer"])
    data["answers"].append({
        "question": q["q"],
        "selected": q["options"][answer],
        "correct_answer": q["options"][q["answer"]],
        "is_correct": correct
    })

    if correct:
        data["score"] += 1

    data["index"] += 1

    if data["index"] < len(data["questions"]):
        next_q = data["questions"][data["index"]]
        buttons = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(next_q["options"])]
        await query.edit_message_text(
            f"سؤال {data['index'] + 1} از {len(data['questions'])}:\n\n{next_q['q']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await finish_exam(query, context, from_query=True)

# پایان آزمون و ذخیره نتایج
async def finish_exam(update_or_query, context: ContextTypes.DEFAULT_TYPE, from_query=False):
    user_id = update_or_query.from_user.id
    data = user_data[user_id]
    data["completed"] = True

    percent = (data["score"] / len(data["questions"])) * 100

    with open(RESULTS_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([user_id, data["name"], data["score"], f"{percent:.1f}%", str(data["answers"])])

    text = f"✅ آزمون تمام شد!\n\n" \
           f"📊 نمره شما: {data['score']} از {len(data['questions'])}\n" \
           f"درصد پاسخ صحیح: {percent:.1f}%\n\n"

    for i, ans in enumerate(data["answers"], start=1):
        mark = "✅" if ans["is_correct"] else "❌"
        text += f"{i}. {ans['question']}\n" \
                f"پاسخ شما: {ans['selected']}  {mark}\n" \
                f"پاسخ صحیح: {ans['correct_answer']}\n\n"

    if from_query:
        await update_or_query.edit_message_text(text[:4000])
    else:
        await update_or_query.message.reply_text(text[:4000])

# ======== جایگزین کن توکن خودت رو اینجا ========
TOKEN = "8475437543:AAG75xruJgLyAJnyD7WGsZlpsZu3dWs_ejE"

# ساخت اپلیکیشن و اضافه کردن هندلرها
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

# اجرا (Polling ربات)
app.run_polling()
