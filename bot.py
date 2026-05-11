import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =========================
# ФАЙЛ ДАННЫХ
# =========================
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "pending_payments": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================
# СОСТОЯНИЯ
# =========================
class TarotState(StatesGroup):
    waiting_question = State()
    waiting_spread_type = State()
    waiting_spread_theme = State()

class AdminState(StatesGroup):
    pass

# =========================
# СОВЕТЫ (РАНДОМНЫЕ)
# =========================
tips = [
    "🌟 Звезды советуют: прислушайся к первому импульсу — он самый чистый.",
    "💫 Луна шепчет: твоя интуиция сейчас сильнее логики.",
    "🔥 Марс советует: не бойся действовать смело, Вселенная поддержит.",
    "🌿 Венера напоминает: любовь начинается с принятия себя.",
    "⚖️ Юпитер говорит: расширяй горизонты, удача на твоей стороне.",
    "🪷 Сатурн учит: терпение — твоя суперсила сегодня.",
    "☀️ Солнце сияет: улыбнись, светлый период уже близко.",
    "🌙 Меркурий советует: будь гибким в общении, слова имеют силу.",
    "💎 Северный узел ведёт: не оглядывайся, твой путь впереди.",
    "🔮 Хирон напоминает: исцели прошлое — и будущее улыбнётся.",
]

# =========================
# РАСШИРЕННЫЕ ТРАКТОВКИ ПО КАТЕГОРИЯМ
# =========================
theme_meanings = {
    "love": {
        "upright": "✨ В сердечных делах {card} сулит {meaning}. Энергия любви сейчас мощна как никогда. Твои чувства настоящи, а если сомневаешься — прислушайся к телу, оно не врёт. Отношения войдут в новую фазу в ближайшие дни. Если одна — готовься к встрече. Если в паре — жди углубления связи.",
        "reversed": "🌙 В любви {card} перевёрнутый говорит о {meaning}. Возможно, ты закрываешь глаза на очевидное. Страх близости или старые обиды мешают. Позволь себе быть уязвимым — это откроет дверь к настоящей гармонии."
    },
    "money": {
        "upright": "💰 В финансах {card} пророчит {meaning}. Денежный поток активируется, но не сиди сложа руки — лови возможности. Удача любит подготовленных. Ближайшие недели принесут неожиданные поступления или выгодное предложение.",
        "reversed": "📉 {card} перевёрнутый предупреждает: {meaning}. Финансовая энергия заблокирована из-за страха или жадности. Пересмотри своё отношение к деньгам. Они приходят к тем, кто отпустил контроль."
    },
    "career": {
        "upright": "💼 В работе и карьере {card} означает {meaning}. Твой потенциал замечен. Возможно повышение, похвала от начальства или интересный проект. Действуй профессионально — результат превзойдёт ожидания.",
        "reversed": "🌀 {card} перевёрнутый в делах говорит: {meaning}. Ты выгораешь или размениваешься на неважное. Остановись, пересмотри приоритеты. Смена деятельности или отдых вернут энергию."
    },
    "general": {
        "upright": "🔮 В твоей ситуации {card} приносит {meaning}. Вселенная выстраивает события так, чтобы ты вырос. Доверяй процессу даже если сейчас непонятно. Скоро всё встанет на свои места.",
        "reversed": "🌑 {card} перевёрнутый показывает: {meaning}. Сопротивление течению создаёт дискомфорт. Расслабься, прими то, что есть — и увидишь выход."
    }
}

# =========================
# КАРТЫ ТАРО (80шт с трактовками)
# =========================
cards_data = {
    "Шут": {"upright": "новое начало, свободу, прыжок веры", "reversed": "безрассудство, страх перед шагом, детскую наивность"},
    "Маг": {"upright": "силу воли, ресурсы, мастерство", "reversed": "манипуляции, неуверенность, потерю фокуса"},
    "Верховная Жрица": {"upright": "интуицию, тайны, мудрость молчания", "reversed": "заблокированное чутьё, иллюзии, неговорящие знаки"},
    "Императрица": {"upright": "плодородие, творчество, изобилие", "reversed": "лень, застой, зависимость от других"},
    "Император": {"upright": "структуру, власть, стабильность", "reversed": "тиранию, хаос, отсутствие границ"},
    "Иерофант": {"upright": "традиции, наставника, правильный путь", "reversed": "бунт, ложные учения, разрыв с родом"},
    "Влюбленные": {"upright": "выбор сердца, гармонию, союз", "reversed": "разлад, неверное решение, внутренний конфликт"},
    "Колесница": {"upright": "победу, волю, движение вперёд", "reversed": "потерю контроля, агрессию, препятствия"},
    "Сила": {"upright": "смелость, терпение, внутреннюю мощь", "reversed": "слабость, страх, эмоциональный взрыв"},
    "Отшельник": {"upright": "мудрость, покой, поиск истины", "reversed": "одиночество, изоляцию, отчаяние"},
    "Колесо Фортуны": {"upright": "перемены, удачу, поворот судьбы", "reversed": "неудачу, сопротивление, застой"},
    "Справедливость": {"upright": "честность, карму, баланс", "reversed": "несправедливость, ложь, уход от ответа"},
    "Повешенный": {"upright": "паузу, жертву, новый взгляд", "reversed": "застревание, бесполезную жертву, эгоизм"},
    "Смерть": {"upright": "трансформацию, конец цикла, рождение нового", "reversed": "страх перемен, сопротивление, гниение старого"},
    "Умеренность": {"upright": "баланс, терпение, гармонию", "reversed": "дисбаланс, нетерпение, конфликт"},
    "Дьявол": {"upright": "привязанность, иллюзию, зависимости", "reversed": "освобождение, разрыв цепей, прозрение"},
    "Башня": {"upright": "крах, внезапные перемены, шок", "reversed": "избегание кризиса, затянутое разрушение"},
    "Звезда": {"upright": "надежду, вдохновение, исцеление", "reversed": "отчаяние, потерю веры, апатию"},
    "Луна": {"upright": "иллюзии, страхи, глубины подсознания", "reversed": "прояснение, раскрытие обмана, победу над страхом"},
    "Солнце": {"upright": "радость, успех, счастье", "reversed": "пессимизм, временные трудности, эгоизм"},
    "Суд": {"upright": "пробуждение, прощение, новый шанс", "reversed": "самообман, нежелание меняться, потерю возможности"},
    "Мир": {"upright": "завершение, целостность, награду", "reversed": "незавершённость, пустоту, задержку результата"},
}
# Добавим ещё младших арканов для разнообразия
minors = ["Туз", "Двойка", "Тройка", "Четверка", "Пятерка", "Шестерка", "Семерка", "Восьмерка", "Девятка", "Десятка", "Паж", "Рыцарь", "Королева", "Король"]
suits = ["Жезлов", "Кубков", "Мечей", "Пентаклей"]
for suit in suits:
    for minor in minors:
        name = f"{minor} {suit}"
        if minor == "Туз":
            u = f"начало в сфере {suit.lower()}, чистый потенциал, первый шаг"
            r = f"упущенный шанс, задержку старта, блокировку энергии"
        elif minor in ["Королева", "Король"]:
            u = f"зрелую энергию {suit.lower()}, мудрость, влияние"
            r = f"злоупотребление властью, холодность, доминирование"
        else:
            u = f"постепенное развитие в {suit.lower()}, стабильность, рост"
            r = f"застой, мелкие препятствия, потерю темпа"
        cards_data[name] = {"upright": u, "reversed": r}

# =========================
# КЛАВИАТУРЫ (все кнопки под сообщениями)
# =========================
main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🃏 Расклад на вопрос", callback_data="spread_single")],
    [InlineKeyboardButton(text="🔮 Расклад 3 карты", callback_data="spread_three")],
    [InlineKeyboardButton(text="❤️ Любовь", callback_data="theme_love")],
    [InlineKeyboardButton(text="💰 Финансы", callback_data="theme_money")],
    [InlineKeyboardButton(text="💼 Карьера", callback_data="theme_career")],
    [InlineKeyboardButton(text="🎁 Бесплатный вопрос дня", callback_data="free")],
    [InlineKeyboardButton(text="💎 Купить вопросы", callback_data="buy")],
    [InlineKeyboardButton(text="📊 Мой баланс", callback_data="balance")],
])

back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
])

tariff_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔮 3 вопроса — 50 ₽", callback_data="3_50")],
    [InlineKeyboardButton(text="✨ 8 вопросов — 100 ₽", callback_data="8_100")],
    [InlineKeyboardButton(text="🌟 15 вопросов — 350 ₽", callback_data="15_350")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
])

# =========================
# ФУНКЦИИ
# =========================
def get_user(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"questions_left": 1, "last_free_date": None, "total_asked": 0}
        save_data(data)
    return data["users"][uid]

def update_user(user_id, key, value):
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        get_user(user_id)
    data["users"][uid][key] = value
    save_data(data)

def can_get_free(user_id):
    user = get_user(user_id)
    last = user.get("last_free_date")
    if not last:
        return True
    try:
        last_date = datetime.fromisoformat(last)
        return datetime.now() - last_date >= timedelta(days=1)
    except:
        return True

def use_free_question(user_id):
    if can_get_free(user_id):
        update_user(user_id, "last_free_date", datetime.now().isoformat())
        return True
    return False

def draw_card():
    name = random.choice(list(cards_data.keys()))
    is_rev = random.choice([True, False])
    meaning_text = cards_data[name]["reversed" if is_rev else "upright"]
    return name, "перевёрнутая" if is_rev else "прямая", meaning_text

def get_full_reading(card_name, position, meaning, theme, question):
    theme_key = theme.replace("theme_", "") if theme.startswith("theme_") else "general"
    if theme_key not in theme_meanings:
        theme_key = "general"
    template = theme_meanings[theme_key]["reversed" if "перевёрнутая" in position else "upright"]
    reading = template.format(card=card_name, meaning=meaning)
    # Добавляем вопрос в трактовку
    reading += f"\n\n📩 Твой вопрос: «{question}». Карты видят его суть."
    return reading

def get_three_cards_reading(question, theme):
    cards_res = []
    for _ in range(3):
        name, pos, mean = draw_card()
        cards_res.append((name, pos, mean))
    # Общая трактовка
    combined = " ".join([c[2] for c in cards_res])
    if "любов" in question.lower() or theme == "love":
        general = f"💞 В любви три карты говорят: {combined}. Энергия отношений переплетается. Судьба ведёт тебя к важной встрече или пересмотру текущей связи. Открой сердце."
    elif "денег" in question.lower() or "финанс" in question.lower() or theme == "money":
        general = f"💰 Деньги: {combined}. Финансовый поток усилится после твоего действия. Избегай импульсивных трат."
    elif "работ" in question.lower() or theme == "career":
        general = f"💼 Карьера: {combined}. Профессиональный рост неизбежен. Будь внимателен к знакам."
    else:
        general = f"🔮 Общий поток: {combined}. Вселенная готовит сюрприз. Расслабься и позволь событиям идти своим чередом."
    return cards_res, general

# =========================
# ОБРАБОТЧИКИ
# =========================
@dp.message(CommandStart())
async def start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer(
        "🌟 **Добро пожаловать в Оракул Таро** 🌟\n\n"
        "Здесь древние карты говорят с тобой без посредников. Каждый расклад — это разговор с душой мира.\n\n"
        "✨ **Что ты найдёшь здесь?**\n"
        "• Глубокие трактовки, которые отзовутся в сердце\n"
        "• Расклады на любовь, деньги, карьеру и любые вопросы\n"
        "• Бесплатный вопрос каждый день\n\n"
        "Выбери то, что сейчас важнее всего 👇",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌟 Главное меню — выбери расклад или тему:",
        reply_markup=main_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"📊 **Твой баланс:**\n\n"
        f"🎴 Осталось вопросов: **{user['questions_left']}**\n"
        f"📆 Всего раскладов: {user.get('total_asked', 0)}\n"
        f"🎁 Следующий бесплатный: завтра\n\n"
        f"➕ Пополнить баланс: кнопка «💎 Купить вопросы»",
        reply_markup=back_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "free")
async def free_question(callback: CallbackQuery, state: FSMContext):
    if use_free_question(callback.from_user.id):
        await callback.message.edit_text(
            "🎁 **Бесплатный вопрос дня активирован!**\n\n"
            "Напиши свой вопрос:",
            reply_markup=back_keyboard
        )
        await state.set_state(TarotState.waiting_question)
        await state.update_data(theme="general", spread="single")
    else:
        await callback.message.edit_text(
            "❌ Ты уже использовал бесплатный вопрос сегодня.\n"
            "Вернись завтра или купи платные вопросы.",
            reply_markup=back_keyboard
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("theme_"))
async def choose_theme(callback: CallbackQuery, state: FSMContext):
    theme = callback.data
    await state.update_data(theme=theme)
    await callback.message.edit_text(
        f"📝 Теперь напиши свой вопрос по этой теме.\n\n"
        f"Примеры:\n"
        f"• Что меня ждёт в ближайшее время?\n"
        f"• Как ко мне относится ...?\n"
        f"• Стоит ли начинать проект?",
        reply_markup=back_keyboard
    )
    await state.set_state(TarotState.waiting_question)
    await state.update_data(spread="single")
    await callback.answer()

@dp.callback_query(F.data == "spread_single")
async def single_spread(callback: CallbackQuery, state: FSMContext):
    await state.update_data(spread="single", theme="general")
    await callback.message.edit_text(
        "🔮 **Расклад 1 карта**\n\n"
        "Напиши свой вопрос. Он может быть о любом — карты ответят честно.",
        reply_markup=back_keyboard
    )
    await state.set_state(TarotState.waiting_question)
    await callback.answer()

@dp.callback_query(F.data == "spread_three")
async def three_spread(callback: CallbackQuery, state: FSMContext):
    await state.update_data(spread="three", theme="general")
    await callback.message.edit_text(
        "🃏 **Расклад 3 карты**\n\n"
        "Прошлое → Настоящее → Будущее\n\n"
        "Напиши свой вопрос.",
        reply_markup=back_keyboard
    )
    await state.set_state(TarotState.waiting_question)
    await callback.answer()

@dp.message(TarotState.waiting_question)
async def handle_question(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    spread = data.get("spread", "single")
    theme = data.get("theme", "general")
    question = message.text.strip()

    user = get_user(user_id)
    if user["questions_left"] <= 0:
        await message.answer(
            "❌ У тебя закончились вопросы!\nПополни баланс в меню.",
            reply_markup=main_keyboard
        )
        await state.clear()
        return

    # Списываем вопрос
    update_user(user_id, "questions_left", user["questions_left"] - 1)
    update_user(user_id, "total_asked", user.get("total_asked", 0) + 1)

    tip = random.choice(tips)

    if spread == "three":
        cards_res, general = get_three_cards_reading(question, theme)
        text = f"🔮 **Расклад 3 карты**\n📩 Вопрос: _{question}_\n\n"
        positions = ["Прошлое", "Настоящее", "Будущее"]
        for i, (name, pos, mean) in enumerate(cards_res):
            text += f"🃏 **{positions[i]}** — {name} ({pos})\n✨ {mean}\n\n"
        text += f"🌟 **Общая трактовка:**\n{general}\n\n"
        text += f"💫 **Совет:** {tip}\n\n"
        text += f"📊 Осталось вопросов: {user['questions_left'] - 1}"
    else:
        name, pos, mean = draw_card()
        full_reading = get_full_reading(name, pos, mean, theme, question)
        text = f"🃏 **Карта:** {name} ({pos})\n\n{full_reading}\n\n💫 {tip}\n\n📊 Осталось вопросов: {user['questions_left'] - 1}"

    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)
    await state.clear()

# =========================
# ПОКУПКА
# =========================
@dp.callback_query(F.data == "buy")
async def buy_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💸 **Выбери пакет вопросов:**\n\n"
        "3 вопроса — 50 ₽\n8 вопросов — 100 ₽\n15 вопросов — 350 ₽\n\n"
        "💳 Реквизиты Тинькофф: **89512694834**\n"
        "В комментарии укажи свой Telegram ID.\n\n"
        "📸 После оплаты отправь скрин чека сюда — администратор начислит вопросы.",
        reply_markup=tariff_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data.startswith(("3_50", "8_100", "15_350")))
async def tariff_chosen(callback: CallbackQuery, state: FSMContext):
    tariff_map = {"3_50": 3, "8_100": 8, "15_350": 15}
    qty = tariff_map[callback.data]
    await state.update_data(pending_qty=qty)
    await callback.message.edit_text(
        f"✅ Ты выбрал {qty} вопросов.\n\n"
        f"💳 Оплати на номер **89512694834** (Тинькофф) с комментарием: «Таро {qty}»\n"
        f"📸 После оплаты пришли скрин чека в этот чат.\n\n"
        f"🔔 Администратор проверит и начислит вопросы вручную.",
        reply_markup=back_keyboard
    )
    await callback.answer()

@dp.message(F.photo)
async def payment_screenshot(message: types.Message):
    user_id = message.from_user.id
    await message.answer(
        "📸 Спасибо, скрин получен!\n\n"
        "Администратор проверит оплату и начислит вопросы в ближайшее время.",
        reply_markup=main_keyboard
    )
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"💰 Новый скрин чека от @{message.from_user.username} (ID: {user_id})\n"
            f"Начисли вопросы командой: /add_questions {user_id} [количество]"
        )

# =========================
# АДМИН КОМАНДЫ
# =========================
@dp.message(Command("add_questions"))
async def add_questions_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        user = get_user(user_id)
        new_bal = user["questions_left"] + amount
        update_user(user_id, "questions_left", new_bal)
        await message.answer(f"✅ Добавлено {amount} вопросов пользователю {user_id}. Баланс: {new_bal}")
        await bot.send_message(user_id, f"✨ Администратор добавил тебе {amount} вопросов! Баланс: {new_bal}. Приятного гадания 🌙")
    except:
        await message.answer("❌ Формат: /add_questions user_id количество")

@dp.message(Command("all_users"))
async def all_users_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    text = "📊 Пользователи:\n"
    for uid, info in data["users"].items():
        text += f"👤 {uid}: {info['questions_left']} вопросов, всего {info.get('total_asked',0)}\n"
    await message.answer(text[:4000])

@dp.message(Command("admin"))
async def admin_help(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "👑 Админ команды:\n"
        "/add_questions user_id количество\n"
        "/all_users — список пользователей\n"
        "/admin — помощь"
    )

# =========================
# WEB-СЕРВЕР ДЛЯ ПИНГА (чтобы Render не засыпал)
# =========================
from aiohttp import web

async def health_check(request):
    return web.Response(text="I am alive!")

async def start_web_app():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    await site.start()

async def main():
    # Запускаем веб-сервер для пингов (чтобы Render не засыпал)
    await start_web_app()
    print("✅ Web-сервер для Health Check запущен на порту 8080")
    print("✅ Бот Таро запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
