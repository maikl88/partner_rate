import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

def login_to_1c(username, password):
    # URL страницы авторизации
    login_url = "https://login.1c.ru/login?service=https%3A%2F%2Fits.1c.eu%2Flogin%2F%3Faction%3Daftercheck%26provider%3Dlogin"
    
    # Создаем сессию для сохранения cookies между запросами
    session = requests.Session()
    
    # Получаем страницу авторизации для извлечения скрытых полей
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Находим форму и извлекаем скрытые поля
    login_form = soup.find('form', {'id': 'loginForm'})
    hidden_fields = {}
    
    # Извлекаем значения скрытых полей, если они есть
    if login_form:
        for hidden_field in login_form.find_all('input', type='hidden'):
            name = hidden_field.get('name')
            value = hidden_field.get('value', '')
            hidden_fields[name] = value
    
        # Создаем данные для отправки формы
        form_data = {
            'username': username,
            'password': password,
            **hidden_fields  # Добавляем скрытые поля
        }
        
        # Находим URL для отправки формы
        form_action = login_form.get('action')
        if form_action.startswith('/'):
            submit_url = f"https://login.1c.ru{form_action}"
        else:
            submit_url = form_action
    else:
        # Если форма не найдена, используем стандартный URL
        submit_url = "https://login.1c.ru/login"
        form_data = {
            'username': username,
            'password': password
        }
    
    # Отправляем форму авторизации
    login_response = session.post(
        submit_url,
        data=form_data,
        headers={
            'Referer': login_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        allow_redirects=True  # Разрешаем перенаправления
    )
    
    # Проверяем успешность авторизации по финальному URL после перенаправлений
    if 'its.1c.eu' in login_response.url:
        print("Авторизация успешна!")
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

def download_file(session, url, output_folder='downloads'):
    try:
        # Создаем папку для загрузок, если она не существует
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Получаем имя файла из URL или генерируем имя на основе текущей даты/времени
        file_name = url.split('/')[-1]
        if '?' in file_name:  # Если URL содержит параметры запроса
            # Создаем имя на основе даты и расширения из URL
            extension = 'xml' if 'export.xml' in url else 'txt'
            file_name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        
        file_path = os.path.join(output_folder, file_name)
        
        # Отправляем запрос на получение файла
        print(f"Скачивание файла с URL: {url}")
        response = session.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            stream=True  # Используем потоковую передачу для больших файлов
        )
        
        # Проверяем успешность запроса
        if response.status_code == 200:
            # Сохраняем файл
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Файл успешно сохранен: {file_path}")
            return file_path
        else:
            print(f"Ошибка при скачивании файла. Код ответа: {response.status_code}")
            print(f"Текст ответа: {response.text[:500]}...")  # Выводим первые 500 символов ответа
            return None
    except Exception as e:
        print(f"Произошла ошибка при скачивании файла: {str(e)}")
        return None

def main():
    username = "***"  # Замените на ваш логин
    password = "***"  # Замените на ваш пароль
    
    session = login_to_1c(username, password)
    
    if session:
        # URL файла для скачивания
        file_url = "https://its.1c.eu/partner/rating/export.xml?city=&region=%D0%9A%D1%8B%D1%80%D0%B3%D1%8B%D0%B7%D1%81%D1%82%D0%B0%D0%BD&date=03.2025"
        
        # Скачиваем файл
        downloaded_file = download_file(session, file_url)
        
        if downloaded_file:
            print(f"Файл успешно скачан и сохранен по пути: {downloaded_file}")
            
            # Опционально: проверяем содержимое скачанного файла
            try:
                with open(downloaded_file, 'r', encoding='utf-8') as f:
                    first_lines = ''.join(f.readlines()[:5])  # Читаем первые 5 строк
                    print("\nПервые строки файла:")
                    print(first_lines)
            except UnicodeDecodeError:
                print("\nФайл содержит данные в двоичном формате или другой кодировке, не UTF-8")
                
                # Пробуем открыть в другой кодировке
                try:
                    with open(downloaded_file, 'r', encoding='cp1251') as f:
                        first_lines = ''.join(f.readlines()[:5])
                        print("\nПервые строки файла (cp1251):")
                        print(first_lines)
                except:
                    print("Не удалось отобразить содержимое файла")

if __name__ == "__main__":
    main()
