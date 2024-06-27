import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from epicstore_api import EpicGamesStoreAPI
from datetime import datetime, timedelta
from aiogram import types as aiogram_types
import aioschedule
from dateutil import parser
import os
from keep_alive import keep_alive
import psycopg2
from dotenv import load_dotenv
keep_alive()

try:
    load_dotenv()
except:
    print('error loading variables from .env')

try:
        conn = psycopg2.connect(
        dbname=os.environ.get('dbname'),
        user=os.environ.get('user'),
        password=os.environ.get('password'),
        host=os.environ.get('host'),
        port=os.environ.get('port')
                                    )
        print("Connected to database successfully!")
        cur = conn.cursor()
except psycopg2.Error as e:
        print("Unable to connect to the database:", e)



try:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS botdb (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            tg_id BIGINT NOT NULL,
            UNIQUE (name, tg_id)
        )
    """)
    conn.commit()
    print("Table created successfully!")

except:
    print("Error creating table:")


# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.environ.get('token')

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

btn_rus = KeyboardButton(text='🇷🇺 Русский')
btn_en = KeyboardButton(text='🇺🇸 English')
Kb_lang = ReplyKeyboardMarkup(
    keyboard=[[btn_rus, btn_en]],
    resize_keyboard=True,
    one_time_keyboard=True
)

btn_refresh_en = KeyboardButton(text='🔄 Refresh')
btn_lang_en = KeyboardButton(text='🌐 Language')

btn_refresh_ru = KeyboardButton(text='🔄 Обновить')
btn_lang_ru = KeyboardButton(text='🌐 Язык')

btn_announce_ru = KeyboardButton(text='📢 Анонс')
btn_announce_en = KeyboardButton(text='📢 Announcement')

btn_admin_uc = KeyboardButton(text='User Count')

Kb_RU = ReplyKeyboardMarkup(
    keyboard=[[btn_refresh_ru, btn_lang_ru, btn_announce_ru]],
    resize_keyboard=True,
    one_time_keyboard=False
)

Kb_EN = ReplyKeyboardMarkup(
    keyboard=[[btn_refresh_en, btn_lang_en, btn_announce_en]],
    resize_keyboard=True,
    one_time_keyboard=False
)

Kb_Admin = ReplyKeyboardMarkup(
    keyboard=[[btn_refresh_en, btn_lang_en, btn_announce_en, btn_admin_uc]],
    resize_keyboard=True,
    one_time_keyboard=False
)

remove_keyboard = aiogram_types.ReplyKeyboardRemove()

def finder_date(data, title_to_find, datetype):
    for element in data['data']['Catalog']['searchStore']['elements']:
        if element['title'] == title_to_find:
            try:
                end_date = element['promotions']['upcomingPromotionalOffers'][0]['promotionalOffers'][0][datetype]
                return(end_date)
            except:
                end_date = element['promotions']['promotionalOffers'][0]['promotionalOffers'][0][datetype]
                return(end_date)


def schedule_async_ru(schedule_time):
    # Parse the provided datetime string
    scheduled_datetime = parser.parse(schedule_time) + timedelta(minutes=1)

    # Schedule your asynchronous function to run at the specified date and time
    aioschedule.every().day.at(scheduled_datetime.strftime("%H:%M")).do(refresh_ru)

def schedule_async_en(schedule_time):
    # Parse the provided datetime string
    scheduled_datetime = parser.parse(schedule_time) + timedelta(minutes=1)

    # Schedule your asynchronous function to run at the specified date and time
    aioschedule.every().day.at(scheduled_datetime.strftime("%H:%M")).do(refresh_en)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO botdb (name, tg_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (message.from_user.full_name, int(message.from_user.id)))
        print("Entry added successfully!")
        conn.commit()
    except:
        print("Error inserting data:")

    if message.from_user.id == str(os.environ.get('admin_id')):
        await message.answer('👋👋👋', reply_markup=Kb_Admin)
    else:
        await message.answer('👋', reply_markup=Kb_lang)

@dp.message()
async def monitor(message: types.Message) -> None:
    if message.text == '🌐 Язык' or message.text == '🌐 Language':
        await message.answer(text='👋', reply_markup=Kb_lang)
                 
    if message.text == '🇷🇺 Русский' or message.text == '🔄 Обновить':
       await refresh_ru(message)

    if message.text == '🇺🇸 English' or message.text == '🔄 Refresh':
       await refresh_en(message)
    
    if message.text == '📢 Анонс':
        await announce_ru(message)

    if message.text == '📢 Announcement':
        await announce_en(message)
    
    if message.text == 'User Count':
        await usercount(message)


async def usercount(message):

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM botdb")
        row_count = cur.fetchone()[0]
        print("Number of rows:", row_count)
    except:
        print("Error counting rows:")
    await message.answer(f'User count right now is: <b>{str(row_count)}</b>')
async def refresh_ru(message):
    api = EpicGamesStoreAPI(locale='ru-RU', country='RU', session=None)
    free_games = api.get_free_games()
    for i in range(0, len(free_games['data']['Catalog']['searchStore']['elements'])) :
        if free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['discount'] != 0:
            date = finder_date(free_games, free_games['data']['Catalog']['searchStore']['elements'][i]['title'], 'endDate')
            parsed_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=3)
            schedule_async_en(str(parsed_date))
            await message.answer_photo(
                photo = free_games['data']['Catalog']['searchStore']['elements'][i]['keyImages'][1]['url'],
                caption = '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['title'] +' (' + free_games['data']['Catalog']['searchStore']['elements'][i]['effectiveDate'][:4] + ')</b>\n' +
                '\nБез скидки: ' + '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['fmtPrice']['originalPrice'] + '</b>' + 
                '\nБесплатно до: ' + parsed_date.strftime("%d.%m.%Y %H:%M") + ' МСК\n' +
                '\nhttps://store.epicgames.com/ru-RU/p/' + free_games['data']['Catalog']['searchStore']['elements'][i]['catalogNs']['mappings'][0]['pageSlug'] + '\n' +
                '\n' + free_games['data']['Catalog']['searchStore']['elements'][i]['description'], disable_web_page_preview=True, reply_markup=Kb_RU
            )

async def refresh_en(message):
    api = EpicGamesStoreAPI(locale='en-US', country='US', session=None)
    free_games = api.get_free_games()
    for i in range(0, len(free_games['data']['Catalog']['searchStore']['elements'])) :
        if free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['discount'] != 0:
            date = finder_date(free_games, free_games['data']['Catalog']['searchStore']['elements'][i]['title'], 'endDate')
            parsed_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
            schedule_async_en(str(parsed_date))
            await message.answer_photo(
                photo = free_games['data']['Catalog']['searchStore']['elements'][i]['keyImages'][1]['url'],
                caption = '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['title'] +' (' + free_games['data']['Catalog']['searchStore']['elements'][i]['effectiveDate'][:4] + ')</b>\n' +
                '\nOriginal price: ' + '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['fmtPrice']['originalPrice'] + '</b>' + 
                '\nDeal expires: ' + parsed_date.strftime("%d.%m.%Y %H:%M") + ' GMT\n' +
                '\nhttps://store.epicgames.com/en-US/p/' + free_games['data']['Catalog']['searchStore']['elements'][i]['catalogNs']['mappings'][0]['pageSlug'] + '\n' +
                '\n' + free_games['data']['Catalog']['searchStore']['elements'][i]['description'], disable_web_page_preview=True, reply_markup=Kb_EN
            )

async def announce_en(message):
    api = EpicGamesStoreAPI(locale='en-US', country='US', session=None)
    free_games = api.get_free_games()
    for i in range(0, len(free_games['data']['Catalog']['searchStore']['elements'])) :
        if free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['discount'] == 0:
            date_start = finder_date(free_games, free_games['data']['Catalog']['searchStore']['elements'][i]['title'], 'startDate')
            parsed_date_start = datetime.strptime(date_start, "%Y-%m-%dT%H:%M:%S.%fZ")
            date_end = finder_date(free_games, free_games['data']['Catalog']['searchStore']['elements'][i]['title'], 'endDate')
            parsed_date_end = datetime.strptime(date_end, "%Y-%m-%dT%H:%M:%S.%fZ")
            await message.answer_photo(
                photo = free_games['data']['Catalog']['searchStore']['elements'][i]['keyImages'][1]['url'],
                caption = '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['title'] +' (' + free_games['data']['Catalog']['searchStore']['elements'][i]['effectiveDate'][:4] + ')</b>\n' +
                '\nOriginal price: ' + '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['fmtPrice']['originalPrice'] + '</b>' + 
                f'\n<b>From:</b> {parsed_date_start.strftime("%d.%m.%Y %H:%M")} GMT\n<b>To: </b> {parsed_date_end.strftime("%d.%m.%Y %H:%M")} GMT\n' +
                '\nhttps://store.epicgames.com/en-US/p/' + free_games['data']['Catalog']['searchStore']['elements'][i]['catalogNs']['mappings'][0]['pageSlug'] + '\n' +
                '\n' + free_games['data']['Catalog']['searchStore']['elements'][i]['description'], disable_web_page_preview=True, reply_markup=Kb_EN
            )

async def announce_ru(message):
    api = EpicGamesStoreAPI(locale='ru-RU', country='RU', session=None)
    free_games = api.get_free_games()
    for i in range(0, len(free_games['data']['Catalog']['searchStore']['elements'])) :
        if free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['discount'] == 0:
            date_start = finder_date(free_games, free_games['data']['Catalog']['searchStore']['elements'][i]['title'], 'startDate')
            parsed_date_start = datetime.strptime(date_start, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=3)
            date_end = finder_date(free_games, free_games['data']['Catalog']['searchStore']['elements'][i]['title'], 'endDate')
            parsed_date_end = datetime.strptime(date_end, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=3)
            await message.answer_photo(
                photo = free_games['data']['Catalog']['searchStore']['elements'][i]['keyImages'][1]['url'],
                caption = '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['title'] +' (' + free_games['data']['Catalog']['searchStore']['elements'][i]['effectiveDate'][:4] + ')</b>\n' +
                '\nБез скидки: ' + '<b>' + free_games['data']['Catalog']['searchStore']['elements'][i]['price']['totalPrice']['fmtPrice']['originalPrice'] + '</b>' + 
                f'\n<b>От:</b> {parsed_date_start.strftime("%d.%m.%Y %H:%M")} МСК\n<b>До: </b> {parsed_date_end.strftime("%d.%m.%Y %H:%M")} МСК\n' +
                '\nhttps://store.epicgames.com/ru-RU/p/' + free_games['data']['Catalog']['searchStore']['elements'][i]['catalogNs']['mappings'][0]['pageSlug'] + '\n' +
                '\n' + free_games['data']['Catalog']['searchStore']['elements'][i]['description'], disable_web_page_preview=True, reply_markup=Kb_RU
            )

async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    # And the run events dispatching
    await dp.start_polling(bot)
    for i in range(5):
        print(f"Executing other code {i}...")
        await asyncio.sleep(2)


if __name__ == "__main__":
        # Create an event loop
    loop = asyncio.get_event_loop()

    # Run the main function and scheduled tasks concurrently
    loop.create_task(main())
    loop.create_task(aioschedule.run_pending())

    # Keep the event loop running
    loop.run_forever()


    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
