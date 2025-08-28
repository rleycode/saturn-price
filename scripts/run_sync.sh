#!/bin/bash
#
# Скрипт запуска синхронизации Saturn
#

set -e

# Переходим в директорию проекта
cd "$(dirname "$0")/.."

# Активируем виртуальное окружение если есть
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Загружаем переменные окружения
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    
    if ! command -v python3 &> /dev/null; then
        log "ОШИБКА: python3 не найден"
        exit 1
    fi
    
    if [ ! -f "requirements.txt" ]; then
        log "ОШИБКА: requirements.txt не найден"
        exit 1
    fi
    
    # Проверяем основные модули
    python3 -c "import requests, mysql.connector" 2>/dev/null || {
        log "ОШИБКА: Не все зависимости установлены. Запустите: pip install -r requirements.txt"
        exit 1
    }
    
    log "✅ Зависимости в порядке"
}

# Проверка конфигурации
check_config() {
    log "Проверка конфигурации..."
    
    if [ -z "$BITRIX_MYSQL_HOST" ] || [ -z "$BITRIX_MYSQL_DATABASE" ]; then
        log "ОШИБКА: Не заданы обязательные переменные окружения"
        log "Скопируйте .env.example в .env и настройте параметры"
        exit 1
    fi
    
    log "✅ Конфигурация в порядке"
}

# Проверка подключения к Bitrix
test_bitrix_connection() {
    log "Проверка подключения к Bitrix..."
    
    python3 -c "
import sys
sys.path.insert(0, '.')
from bitrix_integration import BitrixClient, BitrixConfig
import os

config = BitrixConfig(
    mysql_host=os.getenv('BITRIX_MYSQL_HOST'),
    mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
    mysql_database=os.getenv('BITRIX_MYSQL_DATABASE'),
    mysql_username=os.getenv('BITRIX_MYSQL_USERNAME'),
    mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD'),
    iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11))
)

try:
    with BitrixClient(config) as client:
        products = client.get_products_by_prefix()
        print(f'✅ Подключение успешно. Найдено товаров Saturn: {len(products)}')
except Exception as e:
    print(f'❌ Ошибка подключения: {e}')
    sys.exit(1)
" || exit 1
}

# Основная функция синхронизации
run_sync() {
    local mode="$1"
    local batch_size="${2:-100}"
    
    log "Запуск синхронизации (режим: $mode, размер пакета: $batch_size)"
    
    case "$mode" in
        "full")
            python3 full_sync.py --batch-size "$batch_size"
            ;;
        "parse-only")
            python3 full_sync.py --parse-only --batch-size "$batch_size"
            ;;
        "process-only")
            python3 full_sync.py --process-only
            ;;
        "test")
            python3 full_sync.py --test-mode --batch-size 10
            ;;
        *)
            log "ОШИБКА: Неизвестный режим: $mode"
            log "Доступные режимы: full, parse-only, process-only, test"
            exit 1
            ;;
    esac
}

# Мониторинг процесса
monitor_sync() {
    log "Мониторинг синхронизации..."
    
    # Проверяем логи
    if [ -f "logs/saturn_parser.log" ]; then
        echo "=== Последние 10 строк лога ==="
        tail -10 logs/saturn_parser.log
    fi
    
    # Проверяем выходные файлы
    if [ -d "output" ]; then
        echo "=== Выходные файлы ==="
        ls -la output/
    fi
    
    # Проверяем блокировки
    if [ -f "/tmp/saturn_full_sync.lock" ] || [ -f "saturn_full_sync.lock" ]; then
        echo "⚠️  Обнаружен файл блокировки - процесс может быть запущен"
    fi
}

# Очистка старых файлов
cleanup() {
    log "Очистка старых файлов..."
    python3 full_sync.py --cleanup
}

# Справка
show_help() {
    cat << EOF
Saturn Parser - Скрипт запуска синхронизации

Использование:
  $0 [КОМАНДА] [ОПЦИИ]

Команды:
  full [SIZE]       Полная синхронизация (по умолчанию)
  parse-only [SIZE] Только парсинг цен с Saturn
  process-only      Только обработка существующих цен
  test              Тестовый режим (10 товаров)
  monitor           Мониторинг состояния
  cleanup           Очистка старых файлов
  check             Проверка системы
  help              Показать эту справку

Примеры:
  $0                    # Полная синхронизация (100 товаров)
  $0 full 50           # Полная синхронизация (50 товаров)
  $0 test              # Тестовый режим
  $0 parse-only 20     # Только парсинг (20 товаров)
  $0 monitor           # Мониторинг

Переменные окружения:
  BITRIX_MYSQL_HOST     Хост MySQL Bitrix
  BITRIX_MYSQL_DATABASE База данных Bitrix
  BITRIX_MYSQL_USERNAME Пользователь MySQL
  BITRIX_MYSQL_PASSWORD Пароль MySQL
  BITRIX_IBLOCK_ID      ID информационного блока
  SUPPLIER_PREFIX       Префикс поставщика (saturn-)

EOF
}

# Главная логика
main() {
    local command="${1:-full}"
    local param="$2"
    
    case "$command" in
        "help"|"-h"|"--help")
            show_help
            ;;
        "check")
            check_dependencies
            check_config
            test_bitrix_connection
            log "✅ Все проверки пройдены"
            ;;
        "monitor")
            monitor_sync
            ;;
        "cleanup")
            cleanup
            ;;
        "full"|"parse-only"|"process-only"|"test")
            check_dependencies
            check_config
            run_sync "$command" "$param"
            ;;
        *)
            log "ОШИБКА: Неизвестная команда: $command"
            show_help
            exit 1
            ;;
    esac
}

# Обработка сигналов
trap 'log "Получен сигнал прерывания, завершаем..."; exit 130' INT TERM

# Запуск
main "$@"
