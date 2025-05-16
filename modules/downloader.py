import os
import requests
from datetime import datetime
import time
from bs4 import BeautifulSoup

def login_to_1c(username, password):
    """
    Авторизуется на сайте 1С и возвращает сессию с куками
    
    Args:
        username (str): Логин для входа
        password (str): Пароль для входа
        
    Returns:
        requests.Session: Сессия с авторизационными куками
    """
    # URL страницы авторизации
    login_url = "https://login.1c.ru/login?service=https%3A%2F%2Fits.1c.eu%2Flogin%2F%3Faction%3Daftercheck%26provider%3Dlogin"
    
    # Создаем сессию для сохранения cookies между запросами
    session = requests.Session()
    
    # Заголовки для имитации браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    session.headers.update(headers)
    
    try:
        # Получаем страницу авторизации
        print("Получение страницы авторизации...")
        response = session.get(login_url)
        response.raise_for_status()
        
        # Парсим HTML для извлечения формы
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Находим форму (используем id='loginForm' или ищем любую форму)
        login_form = soup.find('form', {'id': 'loginForm'})
        if not login_form:
            login_form = soup.find('form')
        
        if not login_form:
            print("Не удалось найти форму авторизации на странице.")
            return None
        
        # Извлекаем скрытые поля из формы
        hidden_fields = {}
        for hidden_field in login_form.find_all('input', {'type': 'hidden'}):
            name = hidden_field.get('name')
            value = hidden_field.get('value', '')
            hidden_fields[name] = value
        
        # Создаем данные для отправки формы
        form_data = {
            'username': username,
            'password': password,
            **hidden_fields  # Добавляем скрытые поля
        }
        
        print(f"Форма содержит следующие поля: {list(form_data.keys())}")
        
        # Находим URL для отправки формы
        form_action = login_form.get('action')
        if form_action:
            if form_action.startswith('/'):
                submit_url = f"https://login.1c.ru{form_action}"
            else:
                submit_url = form_action
        else:
            submit_url = login_url
        
        print(f"Отправка формы авторизации на URL: {submit_url}")
        
        # Отправляем форму авторизации
        login_response = session.post(
            submit_url,
            data=form_data,
            headers={
                'Referer': login_url,
                'User-Agent': headers['User-Agent']
            },
            allow_redirects=True  # Разрешаем перенаправления
        )
        
        login_response.raise_for_status()
        
        # Проверяем успешность авторизации по финальному URL после перенаправлений
        if 'its.1c.eu' in login_response.url:
            print("Авторизация успешна!")
            print(f"Конечный URL: {login_response.url}")
            return session
        else:
            print("Авторизация не удалась.")
            print(f"Конечный URL: {login_response.url}")
            
            # Подробная диагностика
            soup = BeautifulSoup(login_response.text, 'html.parser')
            error_messages = soup.find('div', id='emptyUsernameOrPasswordMessage')
            if error_messages:
                print(f"Ошибка: {error_messages.text.strip()}")
            
            return None
    
    except requests.RequestException as e:
        print(f"Ошибка при авторизации: {e}")
        return None
    except Exception as e:
        print(f"Непредвиденная ошибка при авторизации: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_xml_files(year, months, temp_dir, username, password):
    """
    Загружает XML файлы с сайта для указанного года и месяцев, используя авторизацию
    
    Args:
        year (str): Год для загрузки данных
        months (list): Список месяцев для загрузки
        temp_dir (str): Директория для сохранения файлов
        username (str): Логин для входа
        password (str): Пароль для входа
    
    Returns:
        list: Список путей к загруженным файлам
    """
    # Авторизуемся на сайте
    session = login_to_1c(username, password)
    if not session:
        print("Не удалось авторизоваться. Загрузка файлов невозможна.")
        return []
    
    # Создаем директорию, если она не существует
    os.makedirs(temp_dir, exist_ok=True)
    
    base_url = "https://its.1c.eu/partner/rating/export.xml"
    region_param = "%D0%9A%D1%8B%D1%80%D0%B3%D1%8B%D0%B7%D1%81%D1%82%D0%B0%D0%BD"  # "Кыргызстан" в URL-кодировке
    
    downloaded_files = []
    
    for month in months:
        # Форматируем месяц и год для URL
        date_param = f"{month:02d}.{year}"
        
        # Формируем URL для загрузки
        url = f"{base_url}?city=&region={region_param}&date={date_param}"
        
        print(f"Загрузка файла с URL: {url}")
        
        try:
            # Выполняем запрос с нашей авторизованной сессией
            response = session.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                stream=True  # Используем потоковую передачу для больших файлов
            )
            
            # Проверяем статус ответа
            if response.status_code != 200:
                print(f"Ошибка HTTP {response.status_code} при загрузке данных за {month:02d}.{year}")
                continue
            
            # Создаем имя файла и путь для сохранения
            filename = f"export_{year}_{month:02d}.xml"
            file_path = os.path.join(temp_dir, filename)
            
            # Убеждаемся, что родительская директория существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Получаем содержимое ответа
            content = response.content
            
            # Проверяем размер ответа
            content_size = len(content)
            print(f"Получен ответ размером {content_size} байт")
            
            # Сохраняем файл в бинарном режиме
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Проверяем, что файл сохранен
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print(f"Файл сохранен: {file_path}")
                
                # Пытаемся определить, что это XML
                is_xml = False
                try:
                    # Пробуем прочитать файл как текст и проверить на наличие XML-тегов
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = f.read(200)  # Читаем первые 200 символов
                        is_xml = '<?xml' in first_lines or '<partners>' in first_lines
                except:
                    # Если не получается прочитать как текст, пробуем как бинарный
                    with open(file_path, 'rb') as f:
                        first_bytes = f.read(200)
                        first_bytes_str = first_bytes.decode('utf-8', errors='ignore')
                        is_xml = '<?xml' in first_bytes_str or '<partners>' in first_bytes_str
                
                if is_xml:
                    print(f"Файл содержит XML данные")
                    
                    # Добавляем информацию о файле в список
                    downloaded_files.append({
                        'path': file_path,
                        'year': int(year),
                        'month': month
                    })
                    
                    print(f"Загружен файл за {month:02d}.{year}")
                else:
                    print(f"Файл не содержит XML данные. Содержимое начала файла:")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            print(f.read(500))
                    except:
                        print("Не удалось отобразить содержимое")
            else:
                print(f"Ошибка: файл не сохранен или пуст")
            
            # Добавляем небольшую задержку между запросами
            time.sleep(1)
            
        except requests.RequestException as e:
            print(f"Ошибка сетевого запроса для {month:02d}.{year}: {e}")
        except Exception as e:
            print(f"Непредвиденная ошибка при загрузке файла за {month:02d}.{year}: {e}")
            import traceback
            traceback.print_exc()
    
    # Итоговая информация
    print(f"Всего загружено файлов: {len(downloaded_files)}")
    return downloaded_files