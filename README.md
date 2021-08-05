# Дипломная работа


## VKinder
Все слышали про известное приложение для знакомств - Tinder. Приложение предоставляет простой интерфейс для выбора понравившегося человека. Сейчас в Google Play более 100 миллионов установок.

Используя данные из VK, нужно сделать сервис намного лучше, чем Tinder, а именно: чат-бота "VKinder". 
Бот должен искать людей, подходящих под условия, на основании информации о пользователе из VK:
- возраст,
- пол,
- город,
- семейное положение.

У тех людей, которые подошли по требованиям пользователю, получать топ-3 популярных фотографии профиля и отправлять их пользователю в чат вместе со ссылкой на найденного человека.  
Популярность определяется по количеству лайков и комментариев.

За основу можно взять [код из файла basic_code.py](basic_code.py)  
Как настроить группу и получить токен можно найти в [инструкции](group_settings.md)  

## Входные данные
Имя пользователя или его id в ВК, для которого мы ищем пару.
- если информации недостаточно нужно дополнительно спросить её у пользователя.

## Требование к сервису:
1. Код программы удовлетворяет`PEP8`.
2. Получать токен от пользователя с нужными правами.
3. Программа декомпозирована на функции/классы/модули/пакеты.
4. Результат программы записывать в БД.
5. Люди не должны повторяться при повторном поиске.
6. Не запрещается использовать внешние библиотеки для vk.

## Предварительные настройки:
1. Установить зависимости командой: pip3 install -r requirements.txt
2. В файле conf.py необходимо указать токен сообщества и токен приложения VK.

## Использование бота:
- set_token <<TOKEN>> - указываем персональный токен
- find_pairs - запускаем поиск