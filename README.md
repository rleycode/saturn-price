# Saturn Price Parser

Автономный парсер цен с сайта Saturn (https://nnv.saturn.net/) с интеграцией в Bitrix.

## Особенности

- 🚀 **Независимый проект** - не зависит от bitrix-sync
- 🔄 **Четырехэтапный процесс**: парсинг → наценки → обновление Bitrix → скидки
- 🛡️ **Защита от перегрузки** - контроль одновременных запусков
- 📊 **Интеграция с Bitrix** - прямое обновление цен в БД
- 📝 **Детальное логирование** с ротацией файлов
- ⚡ **Автоматизация** через cron с мониторингом

## Быстрый старт

```bash
# Установка
git clone https://github.com/your-repo/saturn-parser.git
cd saturn-parser
pip install -r requirements.txt

# Настройка
cp .env.example .env
nano .env

# Запуск
python saturn_parser.py
```

## Структура проекта

```
saturn-parser/
├── saturn_parser.py          # Основной парсер
├── bitrix_integration.py     # Интеграция с Bitrix
├── markup_processor.py       # Обработка наценок
├── full_sync.py             # Полная синхронизация
├── config/
│   ├── settings.py          # Настройки
│   └── .env.example         # Пример конфигурации
├── utils/
│   ├── logging.py           # Логирование
│   ├── locks.py             # Блокировки
│   └── bitrix_client.py     # Клиент Bitrix
├── scripts/
│   ├── setup_cron.sh        # Настройка автоматизации
│   ├── monitor.sh           # Мониторинг
│   └── run_sync.sh          # Запуск синхронизации
├── docs/
│   ├── INSTALLATION.md      # Установка
│   ├── CONFIGURATION.md     # Настройка
│   └── TROUBLESHOOTING.md   # Решение проблем
└── tests/
    ├── test_parser.py       # Тесты парсера
    └── test_integration.py  # Тесты интеграции
```

## Документация

- [Установка и настройка](docs/INSTALLATION.md)
- [Конфигурация](docs/CONFIGURATION.md)
- [Решение проблем](docs/TROUBLESHOOTING.md)
