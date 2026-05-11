
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import BOT_TOKEN
from tarot import draw_cards
from ai import interpret
from database import init, can_use, add_use

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("🔮 Бот Таро запущен. Напиши свой вопрос.")



@dp.message()
async def handle(msg: types.Message):

    print("MESSAGE RECEIVED:", msg.text)

    user_id = msg.from_user.id

    if not await can_use(user_id):
        await msg.answer("❌ Лимит на сегодня исчерпан")
        return

    cards = draw_cards()

    text_cards = "\n".join([c["name"] for c in cards])

    await msg.answer("🔮 Расклад готов:\n\n" + text_cards)

    # ❌ УБРАЛИ ФОТО

    # AI трактовка
    result = await asyncio.to_thread(interpret, msg.text, text_cards)

    await msg.answer("🧠 Трактовка:\n\n" + result)

    await add_use(user_id)

async def main():
    await init()
    print("BOT STARTED")

    while True:
        try:
            await dp.start_polling(
                bot,
                timeout=60
            )

        except asyncio.CancelledError:
            break

        except Exception as e:
            print("🌐 CONNECTION ERROR:", e)
            print("🔄 retry in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())