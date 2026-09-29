"""All admin-facing bot text, centralized in Uzbek."""

WELCOME = (
    "👋 <b>Nemis tili ta'lim kontenti boti</b>\n\n"
    "Men kanalingiz uchun nemis tili o'rganishga oid postlarni kuniga bir necha marta avtomatik tayyorlayman.\n\n"
    "Har bir qoralama (draft) tasdiqlash uchun shu yerga, shaxsiy chatga yuboriladi. Sizning ruxsatingizsiz "
    "hech narsa kanalga chiqarilmaydi.\n\n"
    "Buyruqlar ro'yxati uchun /yordam ni bosing yoki \"/\" belgisini yozing."
)

HELP = (
    "<b>Mavjud buyruqlar</b>\n\n"
    "/holat — bot, rejalashtiruvchi va bazaning holati\n"
    "/yarat [kategoriya] — qo'lda yangi post yaratish\n"
    "/erkin — o'zingiz xohlagan matn (prompt) bo'yicha post yaratish\n"
    "/rasm — o'zingiz xohlagan tavsif bo'yicha AI rasm yaratish\n"
    "/jadval — bugungi post yaratish vaqtlari\n"
    "/tarix — so'nggi chop etilgan postlar\n"
    "/sozlamalar — joriy sozlamalarni ko'rish\n\n"
    "Yangi qoralama kelganda, tugmalar orqali: Tasdiqlash va chop etish, Yaxshilash yoki "
    "Bekor qilib qayta yaratish mumkin."
)

STATUS_TEMPLATE = (
    "<b>Bot holati</b>\n\n"
    "Bot: Ishlayapti\n"
    "Rejalashtiruvchi: {scheduler_state}\n"
    "Keyingi generatsiya: {next_run}\n"
    "Kanal: {channel}\n"
    "Baza: {db_state}"
)

SCHEDULE_TEMPLATE = "<b>Bugungi jadval</b> ({date}, {timezone})\n\n{lines}"

SETTINGS_TEMPLATE = (
    "<b>Joriy sozlamalar</b>\n\n"
    "Vaqt zonasi: {timezone}\n"
    "Post vaqtlari: {post_times}\n"
    "Standart CEFR darajasi: {cefr}\n"
    "Reklama postlari nisbati: {marketing_ratio}\n"
    "Takrorlanish o'xshashlik chegarasi: {dup_threshold}\n"
    "Maksimal urinishlar soni: {max_attempts}\n"
    "Yangiliklar yoqilganmi: {news_enabled}\n"
    "AI provayder: {llm_provider} ({llm_model})"
)

HISTORY_EMPTY = "Hozircha chop etilgan postlar yo'q."
HISTORY_HEADER = "<b>So'nggi chop etilgan postlar</b>\n\n"

GENERATING = "🔄 Yangi qoralama tayyorlanmoqda..."
GENERATION_FAILED_MANUAL = "⚠️ To'g'ri post yarata olmadim.\n\nSabab: {reason}"
GENERATION_FAILED_SCHEDULED = (
    "⚠️ {slot} vaqti uchun post yarata olmadim.\n\n" "Qo'lda urinib ko'rish uchun /yarat buyrug'ini yuboring."
)

DRAFT_HEADER = "📝 <b>YANGI NEMIS TILI POSTI</b>"
DRAFT_SCHEDULED_SLOT = "Rejalashtirilgan vaqt"
DRAFT_CATEGORY = "Kategoriya"
DRAFT_CEFR = "CEFR darajasi"
DRAFT_STATUS = "Holat"
DRAFT_STATUS_WAITING = "Tasdiqlanishi kutilmoqda"

PUBLISHED_HEADER = "✅ <b>CHOP ETILDI</b>"
PUBLISHED_BODY = "Post kanalga muvaffaqiyatli chop etildi.\n\n<b>Chop etilgan vaqt:</b> {time}"

CHANNEL_FOOTER = "🔗 Kanalga obuna bo'ling: {link}"

DISCARDED_REGENERATING = "❌ Oldingi qoralama bekor qilindi.\n\n🔄 Yangi g'oya tayyorlanmoqda..."
DISCARD_ALREADY_PUBLISHED = "Bu qoralama allaqachon chop etilgan."
DISCARD_REGEN_FAILED = "⚠️ Yangi qoralama yarata olmadim.\n\nQo'lda urinib ko'rish uchun /yarat buyrug'ini yuboring."

IMPROVE_PROMPT = (
    "✏️ Nimani yaxshilashimni xohlaysiz?\n\n"
    "Masalan:\n\n"
    "• Qisqartirish\n"
    "• Qiziqarliroq qilish\n"
    "• Viktorina (quiz) qo'shish\n"
    "• Nemischasini osonlashtirish\n"
    "• O'zbekcha tushuntirish qo'shish\n"
    "• A2 daraja uchun moslashtirish\n"
    "• Emoji qo'shish\n"
    "• Rasmiyroq qilish\n"
    "• Mavzuni o'zgartirish\n"
    "• Reklamani kamaytirish"
)
IMPROVE_REVISING = "✨ Qoralama qayta ishlanmoqda..."
IMPROVE_REVISED_HEADER = "✨ <b>Qayta ishlangan qoralama</b>\n\n"
IMPROVE_FAILED = "⚠️ Qoralamani yaxshilay olmadim: {reason}\n\nQayta urinib ko'ring yoki uni bekor qiling."
IMPROVE_DRAFT_GONE = "Qoralama topilmadi."
IMPROVE_ALREADY_PUBLISHED = "Bu qoralama allaqachon chop etilgan."
IMPROVE_STATE_LOST = "Nimadir xato ketdi. Iltimos, /yarat buyrug'ini qayta yuboring."
IMPROVE_EMPTY_INSTRUCTION = "Iltimos, nimani o'zgartirish kerakligini matn ko'rinishida yozing."

FREEFORM_PROMPT_ASK = (
    "✍️ Nemis tili o'quvchilari uchun qanday post yaratishimni xohlaysiz?\n\n"
    "Masalan: \"Berlindagi jamoat transporti haqida A2 darajasida post yoz\""
)
FREEFORM_EMPTY = "Iltimos, matn ko'rinishida biror so'rov yuboring."
FREEFORM_GENERATING = "🔄 So'rovingiz asosida post tayyorlanmoqda..."
FREEFORM_FAILED = "⚠️ So'rovingiz asosida post yarata olmadim.\n\nSabab: {reason}"

IMAGE_PROMPT_ASK = "🎨 Qanday rasm yaratishimni xohlaysiz? Tavsifini yozing."
IMAGE_EMPTY = "Iltimos, rasm tavsifini matn ko'rinishida yozing."
IMAGE_GENERATING = "🎨 Rasm yaratilmoqda, biroz kuting..."
IMAGE_FAILED = "⚠️ Rasm yarata olmadim.\n\nSabab: {reason}"

UNAUTHORIZED = "⛔ Sizda ushbu botdan foydalanish huquqi yo'q."
INVALID_REQUEST = "Noto'g'ri so'rov."
DRAFT_NOT_FOUND = "Qoralama topilmadi."
ALREADY_PUBLISHED_ALERT = "Bu qoralama allaqachon chop etilgan."
PUBLISH_TELEGRAM_ERROR = "Kanalga chop etib bo'lmadi. Bot huquqlarini tekshiring."
PUBLISHED_ALERT = "Chop etildi!"

BTN_APPROVE = "✅ Tasdiqlash va chop etish"
BTN_IMPROVE = "✏️ Yaxshilash"
BTN_DISCARD = "❌ Bekor qilib qayta yaratish"

CATEGORY_LABELS = {
    "daily_phrases": "Kundalik nemischa",
    "vocabulary": "Lug'at",
    "workplace": "Ish joyida nemischa",
    "grammar": "Grammatika",
    "mistakes": "Umumiy xatolar",
    "comparison": "Nemis va o'zbek tili qiyosi",
    "quiz": "Viktorina",
    "culture": "Germaniya madaniyati",
    "news": "Yangiliklar",
    "media": "Media tavsiyalari",
    "challenge": "O'rganish challenge",
    "migration": "Germaniyada hayot",
    "marketing": "Kurslar haqida",
    "custom": "Erkin so'rov",
}


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.replace("_", " ").title())


BOT_COMMANDS: list[tuple[str, str]] = [
    ("start", "Botni boshlash"),
    ("yordam", "Yordam va buyruqlar ro'yxati"),
    ("holat", "Bot va tizim holatini ko'rish"),
    ("yarat", "Yangi post yaratish (kategoriya tanlab)"),
    ("erkin", "Erkin matn (prompt) bo'yicha post yaratish"),
    ("rasm", "AI yordamida rasm yaratish"),
    ("jadval", "Bugungi post yaratish vaqtlari"),
    ("tarix", "So'nggi chop etilgan postlar"),
    ("sozlamalar", "Joriy sozlamalarni ko'rish"),
]
