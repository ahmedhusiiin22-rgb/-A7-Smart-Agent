import os
import asyncio
import logging
import threading

from flask import Flask
from werkzeug.serving import make_server
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from google import genai

# إعداد السجلات
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("A7")

# المفاتيح السرية
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Missing required environment variables")

# إعداد Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# تعليمات شخصية A7
SYSTEM_PROMPT = """
أنت A7 Smart Agent، مساعد ذكي احترافي لخدمة العملاء.

شخصيتك:
- محترم جداً، مهذب، ودود، ولبق.
- ذكي ودقيق وواضح.
- تتعامل بصبر مع جميع العملاء.
- لا تستخدم أسلوباً متعالياً أو عدوانياً.
- لا تطيل الإجابات دون حاجة.

قواعد التواصل:
1. افهم لغة العميل وأجب باللغة نفسها.
2. تعامل مع العربية والإنجليزية بطلاقة.
3. افهم الأسئلة حتى لو كانت مكتوبة بلهجة عامية.
4. ساعد العميل في فهم المنتجات واختيار المناسب.
5. إذا لم تعرف الإجابة، قل ذلك بوضوح.
6. لا تخترع أسعاراً أو مخزوناً أو عروضاً أو معلومات.
7. لا تؤكد أي عملية شراء أو دفع دون موافقة صاحب المتجر.
8. عند وجود مشكلة لا تستطيع حلها، وجّه العميل إلى خدمة بشرية.
9. حافظ على خصوصية العميل ولا تطلب معلومات حساسة.
10. اجعل كل إجابة مفيدة ومختصرة واحترافية.

اسمك A7 Smart Agent.
"""

# خادم فحص الحالة
health_app = Flask(__name__)

@health_app.route("/")
def health():
    return "A7 Smart Agent is running!", 200

@health_app.route("/health")
def health_check():
    return {"status": "online", "agent": "A7 Smart Agent"}, 200


def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = make_server("0.0.0.0", port, health_app)
    server.serve_forever()


# أمر البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "مرحباً بك! أنا A7 Smart Agent 🤖\n\n"
        "مساعدك الذكي لخدمة العملاء.\n"
        "يسعدني مساعدتك والإجابة عن استفساراتك.\n\n"
        "Hello! I am A7 Smart Agent.\n"
        "How can I help you today?"
    )
    await update.message.reply_text(message)


# أمر المساعدة
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أنا A7 Smart Agent 🤖\n\n"
        "أرسل سؤالك مباشرة وسأحاول مساعدتك.\n"
        "يمكنك التحدث معي بالعربية أو الإنجليزية."
    )


# معالجة رسائل العملاء
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()

    if not user_message:
        return

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        prompt = (
            SYSTEM_PROMPT
            + "\n\nرسالة العميل:\n"
            + user_message
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt
        )

        answer = (response.text or "").strip()

        if not answer:
            answer = "عذراً، لم أتمكن من إعداد إجابة الآن. حاول مرة أخرى."

        # تقسيم الرد إذا كان طويلاً
        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i + 4000])

    except Exception:
        logger.exception("Error while processing customer message")

        await update.message.reply_text(
            "عذراً، حدث عطل مؤقت. حاول مرة أخرى بعد قليل. 🤝"
        )


# تشغيل البوت
def main():
    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("A7 Smart Agent is starting...")

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
