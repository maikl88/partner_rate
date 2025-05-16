import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime

def login_to_1c(username, password):
    """Авторизация на сайте 1С"""
    login_url = "https://login.1c.ru/login?service=https%3A%2F%2Fits.1c.eu%2Flogin%2F%3Faction%3Daftercheck%26provider%3Dlogin"
    session = requests.Session()
    
    # Базовые заголовки для всех запросов
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    session.headers.update(headers)
    
    try:
        # Получаем страницу авторизации
        response = session.get(login_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Находим форму и скрытые поля
        login_form = soup.find('form', {'id': 'loginForm'}) or soup.find('form')
        if not login_form:
            return None
        
        # Получаем скрытые поля
        hidden_fields = {}
        for field in login_form.find_all('input', {'type': 'hidden'}):
            name = field.get('name')
            if name:
                hidden_fields[name] = field.get('value', '')
        
        # URL для отправки формы
        form_action = login_form.get('action', '')
        if form_action.startswith('/'):
            submit_url = f"https://login.1c.ru{form_action}"
        else:
            submit_url = form_action or login_url
        
        # Данные для авторизации
        form_data = {
            'username': username,
            'password': password,
            **hidden_fields
        }
        
        # Отправляем форму
        login_response = session.post(
            submit_url, 
            data=form_data,
            headers={'Referer': login_url},
            allow_redirects=True
        )
        
        # Проверяем успешность авторизации
        if 'its.1c.eu' in login_response.url:
            return session
    except Exception:
        pass
    
    return None

def download_xml_files(year, months, temp_dir, username, password):
    """Загрузка XML-файлов с сайта 1С"""
    session = login_to_1c(username, password)
    if not session:
        return []
    
    os.makedirs(temp_dir, exist_ok=True)
    base_url = "https://its.1c.eu/partner/rating/export.xml"
    region_param = "%D0%9A%D1%8B%D1%80%D0%B3%D1%8B%D0%B7%D1%81%D1%82%D0%B0%D0%BD"  # "Кыргызстан"
    
    downloaded_files = []
    
    for month in months:
        # Формируем URL для загрузки
        date_param = f"{month:02d}.{year}"
        url = f"{base_url}?city=&region={region_param}&date={date_param}"
        
        try:
            # Загружаем файл
            response = session.get(url, stream=True)
            
            if response.status_code == 200:
                # Сохраняем файл
                filename = f"export_{year}_{month:02d}.xml"
                file_path = os.path.join(temp_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Проверяем, что это XML-файл
                if os.path.getsize(file_path) > 0:
                    downloaded_files.append({
                        'path': file_path,
                        'year': int(year),
                        'month': month
                    })
        except Exception:
            pass
    
    return downloaded_files