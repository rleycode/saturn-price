#!/bin/bash
"""
Скрипт установки и настройки Saturn Parser
"""

set -e

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Проверка системы
check_system() {
    log "Проверка системы..."
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        log "ОШИБКА: Python 3 не установлен"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    log "✅ Python версия: $python_version"
    
    # Проверяем pip
    if ! command -v pip3 &> /dev/null; then
        log "ОШИБКА: pip3 не найден"
        exit 1
    fi
    
    log "✅ pip3 доступен"
}

# Создание виртуального окружения
setup_venv() {
    log "Настройка виртуального окружения..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log "✅ Виртуальное окружение создано"
    else
        log "✅ Виртуальное окружение уже существует"
    fi
    
    # Активируем и обновляем pip
    source venv/bin/activate
    pip install --upgrade pip
    log "✅ pip обновлен"
}

# Установка зависимостей
install_dependencies() {
    log "Установка зависимостей..."
    
    if [ ! -f "requirements.txt" ]; then
        log "ОШИБКА: requirements.txt не найден"
        exit 1
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    log "✅ Зависимости установлены"
}

# Настройка конфигурации
setup_config() {
    log "Настройка конфигурации..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log "✅ Создан файл .env из примера"
            log "⚠️  ВНИМАНИЕ: Отредактируйте .env с вашими настройками!"
        else
            log "ОШИБКА: .env.example не найден"
            exit 1
        fi
    else
        log "✅ Файл .env уже существует"
    fi
}

# Создание директорий
create_directories() {
    log "Создание рабочих директорий..."
    
    mkdir -p logs
    mkdir -p output
    mkdir -p config
    mkdir -p tests
    
    log "✅ Директории созданы"
}

# Настройка прав доступа
setup_permissions() {
    log "Настройка прав доступа..."
    
    # Делаем скрипты исполняемыми
    chmod +x scripts/*.sh
    chmod +x *.py
    
    log "✅ Права доступа настроены"
}

# Проверка установки
test_installation() {
    log "Проверка установки..."
    
    source venv/bin/activate
    
    # Тест импорта модулей
    python3 -c "
import requests
import mysql.connector
from bs4 import BeautifulSoup
print('✅ Все модули импортируются корректно')
" || {
        log "❌ Ошибка импорта модулей"
        exit 1
    }
    
    # Тест основных скриптов
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from saturn_parser import SaturnParser
    from bitrix_integration import BitrixClient
    from full_sync import FullSyncManager
    print('✅ Все основные модули загружаются')
except ImportError as e:
    print(f'❌ Ошибка импорта: {e}')
    sys.exit(1)
" || {
        log "❌ Ошибка загрузки основных модулей"
        exit 1
    }
    
    log "✅ Установка проверена успешно"
}

# Создание cron задачи
setup_cron() {
    log "Настройка cron задачи..."
    
    local project_dir=$(pwd)
    local cron_line="0 2 * * * cd $project_dir && ./scripts/run_sync.sh full >> logs/cron.log 2>&1"
    
    # Проверяем, есть ли уже задача
    if crontab -l 2>/dev/null | grep -q "saturn"; then
        log "⚠️  Cron задача для Saturn уже существует"
    else
        # Добавляем новую задачу
        (crontab -l 2>/dev/null; echo "$cron_line") | crontab -
        log "✅ Cron задача добавлена (запуск каждый день в 2:00)"
    fi
}

# Создание systemd сервиса
setup_systemd() {
    log "Настройка systemd сервиса..."
    
    local project_dir=$(pwd)
    local service_file="/etc/systemd/system/saturn-parser.service"
    
    if [ ! -w "/etc/systemd/system/" ]; then
        log "⚠️  Нет прав для создания systemd сервиса (требуется sudo)"
        return
    fi
    
    cat > "$service_file" << EOF
[Unit]
Description=Saturn Price Parser
After=network.target mysql.service

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=$project_dir
Environment=PATH=$project_dir/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$project_dir/scripts/run_sync.sh full
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log "✅ Systemd сервис создан"
    log "Для запуска: sudo systemctl start saturn-parser"
    log "Для автозапуска: sudo systemctl enable saturn-parser"
}

# Создание тестовых данных
create_test_data() {
    log "Создание тестовых данных..."
    
    # Создаем файл с тестовыми артикулами
    cat > test_skus.txt << EOF
# Тестовые артикулы Saturn
ABC123
DEF456
GHI789
JKL012
MNO345
EOF
    
    log "✅ Создан файл test_skus.txt с тестовыми артикулами"
}

# Показать итоговую информацию
show_summary() {
    cat << EOF

🎉 Установка Saturn Parser завершена!

📁 Структура проекта:
   saturn-parser/
   ├── saturn_parser.py          # Основной парсер
   ├── bitrix_integration.py     # Интеграция с Bitrix
   ├── full_sync.py             # Полная синхронизация
   ├── .env                     # Конфигурация (НАСТРОЙТЕ!)
   ├── requirements.txt         # Зависимости
   ├── venv/                    # Виртуальное окружение
   ├── scripts/
   │   ├── run_sync.sh          # Скрипт запуска
   │   └── setup.sh             # Этот скрипт
   ├── logs/                    # Логи
   └── output/                  # Результаты

🔧 Следующие шаги:

1. Настройте .env файл:
   nano .env

2. Проверьте подключение:
   ./scripts/run_sync.sh check

3. Запустите тест:
   ./scripts/run_sync.sh test

4. Полная синхронизация:
   ./scripts/run_sync.sh full

📚 Документация:
   - README.md - основная информация
   - .env.example - пример конфигурации

🚨 ВАЖНО:
   - Обязательно настройте параметры в .env
   - Проверьте подключение к Bitrix MySQL
   - Для продакшена используйте тестовый режим сначала

EOF
}

# Главная функция
main() {
    local skip_cron=false
    local skip_systemd=false
    
    # Обработка аргументов
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-cron)
                skip_cron=true
                shift
                ;;
            --no-systemd)
                skip_systemd=true
                shift
                ;;
            --help|-h)
                cat << EOF
Установка Saturn Parser

Использование: $0 [ОПЦИИ]

Опции:
  --no-cron      Не настраивать cron задачу
  --no-systemd   Не создавать systemd сервис
  --help, -h     Показать эту справку

EOF
                exit 0
                ;;
            *)
                log "Неизвестная опция: $1"
                exit 1
                ;;
        esac
    done
    
    log "🚀 Начинаем установку Saturn Parser..."
    
    # Основные этапы установки
    check_system
    setup_venv
    install_dependencies
    setup_config
    create_directories
    setup_permissions
    create_test_data
    test_installation
    
    # Дополнительные настройки
    if [ "$skip_cron" = false ]; then
        setup_cron
    fi
    
    if [ "$skip_systemd" = false ]; then
        setup_systemd
    fi
    
    show_summary
    log "✅ Установка завершена успешно!"
}

# Обработка сигналов
trap 'log "Установка прервана"; exit 130' INT TERM

# Запуск
main "$@"
