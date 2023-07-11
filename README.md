# TgBotSimpleReminder
Простая напоминалка-бот (ТГ)

Перед началом работы необходимо создать и [активировать виртуальное окружение](https://docs.python.org/3/library/venv.html).

Затем, установить зависимости из requirements.txt командой:
```
pip install -r requirements.txt
```

# Создание .env файла (переменные окружения)
Создать в корне проекта файл .env для хранения переменных окружения (в данном случае - api-key от ТГ-бота, а также таймзону).

Файл .env будет выглять примерно так:
```
BOT_API_KEY=613434349:AAF-zdJFJKFHif46uh5fddi7ufh7d78sdfD4
APS_TIMEZONE=Europe/Moscow
```

# Команды бота
Начать воодить данные (открыть машину состоияний):
```
/go
```
Показать имеющиеся напоминания:
```
/show_tasks
```
Сбросить машину состояний:
```
/cancel
```
Удалить задание:
```
/del_task
```
