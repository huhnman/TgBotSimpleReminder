import datetime

import config

import apscheduler
import apscheduler.jobstores.base

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor


from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# будем хранить прям в оперативной памяти..
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# apscheduler - сам планировщик заданий, чтобы работать с очередями задач (когда задаём время показа уведомлений от бота)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# задаём часовой пояс
sched = AsyncIOScheduler(timezone=config.APS_TIMEZONE)
# чтобы задания выполнялись - необходимо вызвать start()
sched.start()

storage = MemoryStorage()
# Тут - API-ключ от нашего ТГ-бота
tg_bot_api_key = config.BOT_API_KEY


tg_bot = Bot(token=tg_bot_api_key)
dsptchr = Dispatcher(tg_bot, storage=storage)

# хранилище user.id и точек отсчёта времени
time_storage = dict()


# Пропишем класс для работы с машиной состояний (сначала для запроса имени, затем - для вопроса)
class MsgState(StatesGroup):
    user_name = State()
    user_question = State()


# вход в бота
@dsptchr.message_handler(commands=['start'], state=None)
async def init_message(message: types.Message):
    await message.reply("Введите /go если хотите продолжить")


# функция, которая вызывается строго по времени (присылает время, которое прошло с момента последнего сообщения)
async def schedule_reminder(name: str, bot: Bot, chat_id: int):
    # считаем, сколько времени прошло с последнего сообщения
    time_passed = datetime.datetime.now() - time_storage[chat_id]
    total_s = time_passed.total_seconds()

    days, hours, minutes = [i[0:-2] for i in map(str, [total_s // 86400, total_s // 3600, total_s // 60])]

    # функция send_message будет присылать инфу о том, сколько прошло времени
    await bot.send_message(chat_id, f'Привет, {name} ! Прошло времени: {days} дней, {hours} часов, {minutes} минут')


# отмена какого-либо из состояний
@dsptchr.message_handler(state="*", commands=[
    'cancel_this'])  # в данном хендлере отлавливаем ЛЮБОЕ сообщение, даже если работает машина состояний
@dsptchr.message_handler(Text(equals='cancel', ignore_case=True), state="*")
async def cmd_cancel(message: types.Message, state: FSMContext):
    check_st = await state.get_state()
    if check_st is None:
        return
    await state.finish()
    await message.reply('Отменено. Если хотите вновь создать задание - наберите /go')


# хэндлер для перехвата команды 'go' (для начала работы с МАШИНОЙ СОСТОЯНИЙ, и создания задачи)
@dsptchr.message_handler(commands='go', state=None)
async def get_started(message: types.Message):
    # функция set() является точкой входа в машину состояний
    await MsgState.user_name.set()
    await message.reply('Привет ! Введи своё имя')


# Шаг 1: запрашиваем имя у пользователя
@dsptchr.message_handler(state=MsgState.user_name)
async def set_user_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            data['user_name'] = message.text
            await MsgState.next()
            await message.reply('Отлично ! Теперь напиши свой вопрос')

        except:
            await message.reply("Что-то пошло не так... Попробуй ещё раз")


# Шаг 2: узнаём у пользователя вопрос
@dsptchr.message_handler(state=MsgState.user_question)
async def set_user_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            data['user_question'] = message.text

            if sched.get_job(job_id=f'{message.from_user.id}_job') is not None:
                await message.reply(f'У тебя уже есть напоминание !: {message.from_user.id}_job')
                raise apscheduler.jobstores.base.ConflictingIdError(f'{message.from_user.id}_job')

            hours, minutes = datetime.datetime.now().strftime('%H'), datetime.datetime.now().strftime('%M')
            await message.reply(f'Замечательно! Теперь раз в день (т.е. в {hours}:{minutes}) у тебя будут уведомления о прошедшем времени!\n'
                                f'(Начиная с ДАННОГО момента)')

            usr_name = data['user_name']

            # после окончания работы с машиной состояний - необходимо её "закрыть" вызвав функцю finish()
            await state.finish()

            time_storage[message.from_user.id] = datetime.datetime.now()


            # создаём задание
            sched.add_job(schedule_reminder, trigger='cron', hour=f'{hours}',
                          minute=f'{minutes}',
                          id=f'{message.from_user.id}_job',
                          kwargs={'name': usr_name, 'bot': tg_bot, 'chat_id': message.from_user.id})
        except:
            await message.reply('Ох, что-то не то... Повтори')


# Хэндлер для удаления задачи, если не существует - показываем соответствующее сообщение
@dsptchr.message_handler(commands=['del_task'])
async def show_commands(message: types.Message):
    if sched.get_job(job_id=f'{message.from_user.id}_job') is not None:
        sched.remove_job(f'{message.from_user.id}_job')
        await message.reply(f'Задача: {message.from_user.id}_job - была удалена !')
    else:
        await message.reply("Нет задач для удаления!")


# Хэндлер для показа запланированных задач для конкретного юзера
@dsptchr.message_handler(commands=['show_tasks'])
async def show_commands(message: types.Message):
    jobs = sched.get_job(job_id=f'{message.from_user.id}_job')

    if jobs is not None:
        # срезом до -6 элемента, чтобы убрать таймзону
        await message.reply(f"Есть задание. Следующее выполение: {str(jobs.next_run_time)[0:-6]} !")
    else:
        await message.reply(f"Напоминаний нет ! Чтобы создать напоминание - набери /go !")


# Для перехвата команты 'menu' и показа, собственно, меню бота
@dsptchr.message_handler(commands=['menu'])
async def show_commands(message: types.Message):
    await message.reply('Доступные команды:\n/go\n/show_tasks\n/del_task')


# хэндлер на случай, если ввели что-то "не то", будем показывать меню
@dsptchr.message_handler()
async def show_commands(message: types.Message):
    await message.reply('Доступные команды:\n/go\n/show_tasks\n/del_task')


executor.start_polling(dsptchr, skip_updates=True)