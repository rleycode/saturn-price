# Установка Saturn Parser

## Быстрая установка

```bash
# Клонирование проекта
git clone https://github.com/your-repo/saturn-parser.git
cd saturn-parser

# Автоматическая установка
chmod +x scripts/setup.sh
./scripts/setup.sh

# Настройка конфигурации
nano .env

# Проверка установки
./scripts/run_sync.sh check
```

## Ручная установка

### 1. Системные требования

- **Python 3.8+**
- **MySQL 5.7+** (для подключения к Bitrix)
- **Linux/Unix** (рекомендуется)

### 2. Установка зависимостей

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка пакетов
pip install -r requirements.txt
```

### 3. Настройка конфигурации

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование настроек
nano .env
```

**Обязательные параметры:**

```bash
# Подключение к Bitrix MySQL
BITRIX_MYSQL_HOST=localhost
BITRIX_MYSQL_DATABASE=sitemanager
BITRIX_MYSQL_USERNAME=bitrix_sync
BITRIX_MYSQL_PASSWORD=your_password

# Настройки каталога
BITRIX_IBLOCK_ID=11
SUPPLIER_PREFIX=saturn-

# Модуль скидок (опционально)
SATURN_UNDERPRICE_URL=https://your-site.ru/bitrix/admin/underprice.php
SATURN_UNDERPRICE_PASSWORD=your_password
```

### 4. Создание пользователя MySQL

```sql
-- Создание пользователя для Saturn Parser
CREATE USER 'saturn_parser'@'localhost' IDENTIFIED BY 'secure_password';

-- Предоставление прав доступа
GRANT SELECT, INSERT, UPDATE ON sitemanager.b_iblock_element TO 'saturn_parser'@'localhost';
GRANT SELECT, INSERT, UPDATE ON sitemanager.b_iblock_element_property TO 'saturn_parser'@'localhost';
GRANT SELECT, INSERT, UPDATE ON sitemanager.b_catalog_price TO 'saturn_parser'@'localhost';
GRANT SELECT ON sitemanager.b_iblock TO 'saturn_parser'@'localhost';
GRANT SELECT ON sitemanager.b_iblock_property TO 'saturn_parser'@'localhost';
GRANT SELECT ON sitemanager.b_iblock_section TO 'saturn_parser'@'localhost';

FLUSH PRIVILEGES;
```

### 5. Проверка установки

```bash
# Проверка подключения к Bitrix
./scripts/run_sync.sh check

# Тестовый запуск
./scripts/run_sync.sh test
```

## Настройка автоматизации

### Cron (рекомендуется)

```bash
# Добавление задачи в cron
crontab -e

# Добавить строку (запуск каждый день в 2:00)
0 2 * * * cd /path/to/saturn-parser && ./scripts/run_sync.sh full >> logs/cron.log 2>&1
```

### Systemd (альтернатива)

```bash
# Создание сервиса
sudo nano /etc/systemd/system/saturn-parser.service
```

```ini
[Unit]
Description=Saturn Price Parser
After=network.target mysql.service

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/saturn-parser
Environment=PATH=/path/to/saturn-parser/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/path/to/saturn-parser/scripts/run_sync.sh full
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable saturn-parser

# Создание таймера (запуск каждый день в 2:00)
sudo nano /etc/systemd/system/saturn-parser.timer
```

```ini
[Unit]
Description=Run Saturn Parser daily
Requires=saturn-parser.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable saturn-parser.timer
sudo systemctl start saturn-parser.timer
```

## Структура проекта

```
saturn-parser/
├── saturn_parser.py          # Основной парсер цен
├── bitrix_integration.py     # Интеграция с Bitrix
├── full_sync.py             # Полная синхронизация
├── requirements.txt         # Python зависимости
├── .env.example            # Пример конфигурации
├── .env                    # Ваша конфигурация (создается)
├── scripts/
│   ├── run_sync.sh         # Скрипт запуска
│   └── setup.sh            # Скрипт установки
├── docs/
│   ├── INSTALLATION.md     # Этот файл
│   ├── CONFIGURATION.md    # Настройка
│   └── TROUBLESHOOTING.md  # Решение проблем
├── logs/                   # Логи (создается)
├── output/                 # Результаты (создается)
├── venv/                   # Виртуальное окружение (создается)
└── tests/                  # Тесты (создается)
```

## Проверка работоспособности

### 1. Проверка системы

```bash
./scripts/run_sync.sh check
```

**Ожидаемый результат:**
```
✅ Python версия: 3.9.2
✅ pip3 доступен
✅ Зависимости в порядке
✅ Конфигурация в порядке
✅ Подключение успешно. Найдено товаров Saturn: 150
✅ Все проверки пройдены
```

### 2. Тестовый запуск

```bash
./scripts/run_sync.sh test
```

**Ожидаемый результат:**
```
🧪 ТЕСТОВЫЙ РЕЖИМ: ограничено 10 товарами
=== ЭТАП 1: Парсинг цен с Saturn ===
Парсинг товара: ABC123
✅ ABC123: Тестовый товар - 1500.00 руб.
=== ЭТАП 2: Применение наценок и обновление Bitrix ===
✅ saturn-ABC123: 1500.00 → 1950.00 руб.
✅ Полная синхронизация завершена за 45.2с
```

### 3. Мониторинг

```bash
# Просмотр логов
tail -f logs/saturn_parser.log

# Состояние системы
./scripts/run_sync.sh monitor

# Очистка старых файлов
./scripts/run_sync.sh cleanup
```

## Обновление

```bash
# Получение обновлений
git pull origin main

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Проверка после обновления
./scripts/run_sync.sh check
```

## Удаление

```bash
# Остановка cron задач
crontab -e  # удалить строки с saturn

# Остановка systemd сервисов
sudo systemctl stop saturn-parser.timer
sudo systemctl disable saturn-parser.timer
sudo rm /etc/systemd/system/saturn-parser.*

# Удаление проекта
rm -rf /path/to/saturn-parser
```

## Решение проблем

### Ошибка подключения к MySQL

```bash
# Проверка доступности MySQL
mysql -h localhost -u saturn_parser -p

# Проверка прав доступа
SHOW GRANTS FOR 'saturn_parser'@'localhost';
```

### Ошибка импорта модулей

```bash
# Переустановка зависимостей
pip install -r requirements.txt --force-reinstall

# Проверка виртуального окружения
which python3
python3 -c "import sys; print(sys.path)"
```

### Проблемы с правами доступа

```bash
# Исправление прав
chmod +x scripts/*.sh
chmod +x *.py
chown -R your_user:your_group /path/to/saturn-parser
```

Подробнее см. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
