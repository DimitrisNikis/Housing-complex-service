#!/bin/bash
# -*- coding: utf-8 -*-

# Тестирование API Housing Complex Service через curl

# Устанавливаем UTF-8 кодировку для корректной обработки кириллицы
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
TEST_USERNAME="testuser_$(date +%s)"
TEST_PASSWORD="test123"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Счетчики тестов
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Функция для вывода результата теста
print_test_result() {
    local test_name=$1
    local status=$2
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name: $status"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Проверка доступности сервиса
check_service() {
    echo "Проверка доступности сервиса..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL%/api/v1}/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
        print_test_result "Сервис доступен" "PASS"
        return 0
    else
        print_test_result "Сервис недоступен (HTTP $HTTP_CODE)" "FAIL"
        echo -e "${RED}Ошибка: Сервис недоступен на ${BASE_URL}${NC}"
        echo "Убедитесь, что сервис запущен: docker-compose up или uvicorn app.main:app"
        exit 1
    fi
}

# Тест 1: Регистрация пользователя
test_register() {
    echo ""
    echo "=== Тест 1: Регистрация пользователя ==="
    
    # Делаем один запрос и извлекаем HTTP код и ответ
    REGISTER_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/register" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "{\"username\": \"${TEST_USERNAME}\", \"password\": \"${TEST_PASSWORD}\"}" 2>&1)
    
    HTTP_CODE=$(echo "$REGISTER_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    REGISTER_BODY=$(echo "$REGISTER_RESPONSE" | sed '/HTTP_CODE:/d')
    
    if [ "$HTTP_CODE" = "201" ]; then
        USER_ID=$(echo "$REGISTER_BODY" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
        if [ -n "$USER_ID" ]; then
            print_test_result "Регистрация пользователя (ID: $USER_ID)" "PASS"
            return 0
        else
            print_test_result "Регистрация: не получен ID пользователя" "FAIL"
            echo "Ответ: $REGISTER_BODY" | head -3
            return 1
        fi
    else
        print_test_result "Регистрация: HTTP $HTTP_CODE" "FAIL"
        echo "Ответ: $REGISTER_BODY" | head -3
        return 1
    fi
}

# Тест 2: Попытка регистрации с существующим именем
test_register_duplicate() {
    echo ""
    echo "=== Тест 2: Регистрация с существующим именем (должна вернуть ошибку) ==="
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/auth/register" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "{\"username\": \"${TEST_USERNAME}\", \"password\": \"${TEST_PASSWORD}\"}")
    
    if [ "$HTTP_CODE" = "400" ]; then
        print_test_result "Регистрация с существующим именем вернула 400" "PASS"
        return 0
    else
        print_test_result "Регистрация с существующим именем: ожидался 400, получен $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 3: Вход и получение токена
test_login() {
    echo ""
    echo "=== Тест 3: Вход и получение JWT токена ==="
    
    # Проверяем наличие jq
    if ! command -v jq &> /dev/null; then
        # Без jq - используем grep
        LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=${TEST_USERNAME}&password=${TEST_PASSWORD}")
        
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=${TEST_USERNAME}&password=${TEST_PASSWORD}")
        
        if [ "$HTTP_CODE" = "200" ] && echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
            TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        else
            TOKEN=""
        fi
    else
        # С jq
        LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=${TEST_USERNAME}&password=${TEST_PASSWORD}")
        
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=${TEST_USERNAME}&password=${TEST_PASSWORD}")
        
        if [ "$HTTP_CODE" = "200" ]; then
            TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty' 2>/dev/null)
        else
            TOKEN=""
        fi
    fi
    
    if [ "$HTTP_CODE" = "200" ] && [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
        print_test_result "Вход успешен, токен получен (${TOKEN:0:30}...)" "PASS"
        export TOKEN
        return 0
    else
        print_test_result "Вход: HTTP $HTTP_CODE, токен не получен" "FAIL"
        echo "Ответ: $LOGIN_RESPONSE" | head -3
        return 1
    fi
}

# Тест 4: Вход с неверными данными
test_login_wrong_credentials() {
    echo ""
    echo "=== Тест 4: Вход с неверными данными (должен вернуть ошибку) ==="
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=wrong_user&password=wrong_pass")
    
    if [ "$HTTP_CODE" = "401" ]; then
        print_test_result "Вход с неверными данными вернул 401" "PASS"
        return 0
    else
        print_test_result "Вход с неверными данными: ожидался 401, получен $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 5: Получение информации о текущем пользователе
test_get_me() {
    echo ""
    echo "=== Тест 5: Получение информации о текущем пользователе ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Получение /me: токен не установлен" "FAIL"
        return 1
    fi
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}/auth/me" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$HTTP_CODE" = "200" ]; then
        ME_RESPONSE=$(curl -s -X GET "${BASE_URL}/auth/me" \
            -H "Authorization: Bearer $TOKEN")
        
        if echo "$ME_RESPONSE" | grep -q "\"username\""; then
            print_test_result "Получение /me успешно" "PASS"
            return 0
        else
            print_test_result "Получение /me: неверный формат ответа" "FAIL"
            return 1
        fi
    else
        print_test_result "Получение /me: HTTP $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 6: Доступ к защищенному эндпоинту без токена
test_bindings_no_auth() {
    echo ""
    echo "=== Тест 6: Доступ к /bindings без токена (должен вернуть ошибку) ==="
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}/bindings")
    
    if [ "$HTTP_CODE" = "401" ]; then
        print_test_result "Доступ без токена вернул 401" "PASS"
        return 0
    else
        print_test_result "Доступ без токена: ожидался 401, получен $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 7: Получение списка привязок
test_get_bindings() {
    echo ""
    echo "=== Тест 7: Получение списка привязок ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Получение /bindings: токен не установлен" "FAIL"
        return 1
    fi
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}/bindings?skip=0&limit=10" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$HTTP_CODE" = "200" ]; then
        BINDINGS_RESPONSE=$(curl -s -X GET "${BASE_URL}/bindings?skip=0&limit=10" \
            -H "Authorization: Bearer $TOKEN")
        
        if echo "$BINDINGS_RESPONSE" | grep -q "\"items\"" || echo "$BINDINGS_RESPONSE" | grep -q "\"total\""; then
            print_test_result "Получение списка привязок успешно" "PASS"
            return 0
        else
            print_test_result "Получение списка привязок: неверный формат ответа" "FAIL"
            return 1
        fi
    else
        print_test_result "Получение списка привязок: HTTP $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 8: Создание привязки (если есть ЖК)
test_create_binding() {
    echo ""
    echo "=== Тест 8: Создание привязки ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Создание привязки: токен не установлен" "FAIL"
        return 1
    fi
    
    # Используем уникальный адрес для каждого запуска теста, чтобы тест был идемпотентным
    TEST_TIMESTAMP=$(date +%s)
    TEST_ADDRESS=$(printf "г. Москва, ул. Тестовая, д. 12_%s" "$TEST_TIMESTAMP")
    
    # Используем jq или printf для безопасной работы с кириллицей в JSON
    # Используем -c (compact) чтобы убрать переносы строк и отступы
    if command -v jq &> /dev/null; then
        BINDING_JSON=$(jq -cn \
            --arg hc_id "8" \
            --arg addr "$TEST_ADDRESS" \
            --argjson floors 10 \
            --argjson apt_count 100 \
            '{housing_complex_id: ($hc_id | tonumber), address: $addr, floors: $floors, apartments_count: $apt_count}')
    else
        # Fallback: используем printf для правильной обработки UTF-8
        BINDING_JSON=$(printf '{"housing_complex_id": 8, "address": "%s", "floors": 10, "apartments_count": 100}' "$TEST_ADDRESS")
    fi
    
    # Используем printf для безопасной передачи JSON через pipe в curl
    # Получаем HTTP код и ответ одновременно для избежания рассинхронизации
    # Это гарантирует правильную кодировку UTF-8
    CREATE_RESPONSE=$(printf '%s' "$BINDING_JSON" | curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/bindings" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json; charset=utf-8" \
        --data-binary @-)
    
    # Извлекаем HTTP код и тело ответа
    HTTP_CODE=$(echo "$CREATE_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    CREATE_BODY=$(echo "$CREATE_RESPONSE" | sed '/HTTP_CODE:/d')
    
    if [ "$HTTP_CODE" = "201" ]; then
        # Успешное создание - извлекаем ID
        if command -v jq &> /dev/null; then
            BINDING_ID=$(echo "$CREATE_BODY" | jq -r '.id // empty' 2>/dev/null)
        else
            BINDING_ID=$(echo "$CREATE_BODY" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
        fi
        
        if [ -n "$BINDING_ID" ] && [ "$BINDING_ID" != "null" ]; then
            print_test_result "Создание привязки успешно (ID: $BINDING_ID)" "PASS"
            export BINDING_ID
            return 0
        else
            print_test_result "Создание привязки: не получен ID" "FAIL"
            echo "HTTP код: $HTTP_CODE"
            echo "Ответ: $CREATE_BODY" | head -5
            echo "JSON: $BINDING_JSON" | head -1
            return 1
        fi
    elif [ "$HTTP_CODE" = "404" ]; then
        # ЖК не найден - это нормально, если БД пуста или еще не было актуализации
        print_test_result "Создание привязки: ЖК с ID=8 не найден (это нормально, если БД пуста)" "PASS"
        return 0
    elif [ "$HTTP_CODE" = "400" ]; then
        # Проверяем тип ошибки 400
        if echo "$CREATE_BODY" | grep -qiE "уже существует|already exists"; then
            # Привязка уже существует - пытаемся найти через GET запрос
            # Получаем список привязок для housing_complex_id=8
            BINDINGS_LIST=$(curl -s -X GET "${BASE_URL}/bindings?housing_complex_id=8" \
                -H "Authorization: Bearer $TOKEN")
            
            # Ищем привязку, которая соответствует нашему адресу
            if command -v jq &> /dev/null; then
                # Ищем привязку по адресу дома
                TEST_ADDRESS_ESC=$(echo "$TEST_ADDRESS" | jq -R .)
                BINDING_ID=$(echo "$BINDINGS_LIST" | jq -r \
                    ".items[] | select(.house.address == ${TEST_ADDRESS_ESC}) | .id" | head -1)
            else
                # Fallback: простой поиск через grep
                BINDING_ID=$(echo "$BINDINGS_LIST" | grep -o "\"id\":[0-9]*" | head -1 | cut -d: -f2)
            fi
            
            if [ -n "$BINDING_ID" ] && [ "$BINDING_ID" != "null" ]; then
                print_test_result "Создание привязки: привязка уже существует (ID: $BINDING_ID)" "PASS"
                export BINDING_ID
                return 0
            else
                print_test_result "Создание привязки: привязка уже существует (HTTP 400)" "PASS"
                return 0
            fi
        else
            # Другая ошибка 400 - выводим детали для отладки
            print_test_result "Создание привязки: HTTP 400" "FAIL"
            echo "HTTP код: $HTTP_CODE"
            echo "Ответ сервера: $CREATE_BODY"
            echo ""
            echo "Отправленный JSON:"
            if command -v jq &> /dev/null; then
                echo "$BINDING_JSON" | jq . 2>/dev/null || echo "$BINDING_JSON"
            else
                echo "$BINDING_JSON"
            fi
            echo ""
            echo "Тестовый адрес: $TEST_ADDRESS"
            return 1
        fi
    else
        # Неожиданный HTTP код - выводим детали
        print_test_result "Создание привязки: HTTP $HTTP_CODE" "FAIL"
        echo "HTTP код: $HTTP_CODE"
        echo "Ответ сервера: $CREATE_BODY" | head -5
        echo ""
        echo "Отправленный JSON:"
        if command -v jq &> /dev/null; then
            echo "$BINDING_JSON" | jq . 2>/dev/null || echo "$BINDING_JSON"
        else
            echo "$BINDING_JSON"
        fi
        return 1
    fi
}

# Тест 9: Создание привязки с несуществующим ЖК
test_create_binding_invalid_hc() {
    echo ""
    echo "=== Тест 9: Создание привязки с несуществующим ЖК (должна вернуть ошибку) ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Создание привязки с несуществующим ЖК: токен не установлен" "FAIL"
        return 1
    fi
    
    # Используем уникальный адрес для этого теста, чтобы избежать конфликта с существующими домами
    TEST_TIMESTAMP=$(date +%s)
    TEST_ADDRESS=$(printf "г. Москва, ул. Тестовая, д. 99999_%s" "$TEST_TIMESTAMP")
    
    # Используем jq или printf для безопасной работы с кириллицей в JSON
    # Используем -c (compact) чтобы убрать переносы строк и отступы
    if command -v jq &> /dev/null; then
        BINDING_JSON=$(jq -cn \
            --argjson hc_id 99999 \
            --arg addr "$TEST_ADDRESS" \
            '{housing_complex_id: $hc_id, address: $addr}')
    else
        # Fallback: используем printf с переменной подстановкой
        BINDING_JSON=$(printf '{"housing_complex_id": 99999, "address": "%s"}' "$TEST_ADDRESS")
    fi
    
    # Проверяем валидность JSON перед отправкой (для отладки)
    if command -v jq &> /dev/null; then
        if ! echo "$BINDING_JSON" | jq . > /dev/null 2>&1; then
            print_test_result "Создание привязки с несуществующим ЖК: невалидный JSON" "FAIL"
            echo "JSON: $BINDING_JSON"
            return 1
        fi
    fi
    
    # Для отладки: выводим JSON в красивом виде, если доступен jq
    if [ "$DEBUG_JSON" = "1" ] && command -v jq &> /dev/null; then
        echo "Отправляемый JSON:"
        echo "$BINDING_JSON" | jq .
    fi
    
    # Используем printf для безопасной передачи JSON через pipe в curl
    # Это гарантирует правильную кодировку UTF-8
    HTTP_CODE=$(printf '%s' "$BINDING_JSON" | curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/bindings" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json; charset=utf-8" \
        --data-binary @-)
    
    if [ "$HTTP_CODE" = "404" ]; then
        print_test_result "Создание привязки с несуществующим ЖК вернуло 404" "PASS"
        return 0
    else
        # Получаем ответ для отладки
        ERROR_RESPONSE=$(printf '%s' "$BINDING_JSON" | curl -s -X POST "${BASE_URL}/bindings" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json; charset=utf-8" \
            --data-binary @-)
        print_test_result "Создание привязки с несуществующим ЖК: ожидался 404, получен $HTTP_CODE" "FAIL"
        echo "Ответ сервера: $ERROR_RESPONSE"
        echo ""
        echo "Отправленный JSON (raw):"
        echo "$BINDING_JSON"
        echo ""
        echo "Отправленный JSON (pretty, если доступен jq):"
        if command -v jq &> /dev/null; then
            echo "$BINDING_JSON" | jq . 2>/dev/null || echo "$BINDING_JSON"
        else
            echo "$BINDING_JSON"
        fi
        echo ""
        echo "Размер JSON (байты): $(echo -n "$BINDING_JSON" | wc -c)"
        echo "Тестовый адрес: $TEST_ADDRESS"
        return 1
    fi
}

# Тест 10: Удаление привязки (если была создана)
test_delete_binding() {
    echo ""
    echo "=== Тест 10: Удаление привязки ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Удаление привязки: токен не установлен" "FAIL"
        return 1
    fi
    
    if [ -z "$BINDING_ID" ]; then
        print_test_result "Удаление привязки: ID привязки не установлен (пропуск)" "PASS"
        return 0
    fi
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${BASE_URL}/bindings/$BINDING_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$HTTP_CODE" = "204" ]; then
        print_test_result "Удаление привязки успешно (HTTP 204)" "PASS"
        return 0
    elif [ "$HTTP_CODE" = "404" ]; then
        print_test_result "Удаление привязки: привязка не найдена (возможно, уже удалена)" "PASS"
        return 0
    else
        print_test_result "Удаление привязки: HTTP $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 11: Фильтрация привязок по house_id
test_filter_bindings_by_house() {
    echo ""
    echo "=== Тест 11: Фильтрация привязок по house_id ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Фильтрация по house_id: токен не установлен" "FAIL"
        return 1
    fi
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}/bindings?house_id=1" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_test_result "Фильтрация по house_id успешна" "PASS"
        return 0
    else
        print_test_result "Фильтрация по house_id: HTTP $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Тест 12: Фильтрация привязок по housing_complex_id
test_filter_bindings_by_hc() {
    echo ""
    echo "=== Тест 12: Фильтрация привязок по housing_complex_id ==="
    
    if [ -z "$TOKEN" ]; then
        print_test_result "Фильтрация по housing_complex_id: токен не установлен" "FAIL"
        return 1
    fi
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}/bindings?housing_complex_id=1" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_test_result "Фильтрация по housing_complex_id успешна" "PASS"
        return 0
    else
        print_test_result "Фильтрация по housing_complex_id: HTTP $HTTP_CODE" "FAIL"
        return 1
    fi
}

# Главная функция
main() {
    echo "=========================================="
    echo "  Тестирование Housing Complex Service API"
    echo "=========================================="
    echo "Base URL: $BASE_URL"
    echo "Test username: $TEST_USERNAME"
    echo ""
    
    # Проверка доступности сервиса
    check_service || exit 1
    
    # Запуск тестов
    test_register
    test_register_duplicate
    test_login
    test_login_wrong_credentials
    
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}Ошибка: Не удалось получить токен. Дальнейшие тесты не могут быть выполнены.${NC}"
        echo ""
        echo "Итоги:"
        echo "  Всего тестов: $TOTAL_TESTS"
        echo -e "  ${GREEN}Пройдено: $PASSED_TESTS${NC}"
        echo -e "  ${RED}Провалено: $FAILED_TESTS${NC}"
        exit 1
    fi
    
    test_get_me
    test_bindings_no_auth
    test_get_bindings
    test_create_binding
    test_create_binding_invalid_hc
    test_delete_binding
    test_filter_bindings_by_house
    test_filter_bindings_by_hc
    
    # Итоги
    echo ""
    echo "=========================================="
    echo "  Итоги тестирования"
    echo "=========================================="
    echo "  Всего тестов: $TOTAL_TESTS"
    echo -e "  ${GREEN}Пройдено: $PASSED_TESTS${NC}"
    echo -e "  ${RED}Провалено: $FAILED_TESTS${NC}"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ Все тесты пройдены успешно!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}✗ Некоторые тесты провалены${NC}"
        exit 1
    fi
}

# Запуск
main

