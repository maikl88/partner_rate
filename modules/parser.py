import xml.etree.ElementTree as ET
import pandas as pd
import codecs
import os

def parse_xml_data(xml_files):
    """
    Парсит данные из XML файлов
    
    Args:
        xml_files (list): Список словарей с информацией о загруженных файлах
    
    Returns:
        dict: Словарь с данными партнеров по месяцам
    """
    # Структура для хранения данных
    parsed_data = {
        'partners': {},  # Информация о партнерах
        'months': []     # Список обработанных месяцев
    }
    
    # Сортируем файлы по месяцам
    xml_files.sort(key=lambda x: x['month'])
    
    # Для отладки - показываем, что мы обрабатываем
    print(f"Всего файлов для обработки: {len(xml_files)}")
    
    for file_info in xml_files:
        file_path = file_info['path']
        year = file_info['year']
        month = file_info['month']
        month_key = f"{year}_{month:02d}"
        
        print(f"Обработка файла: {file_path}")
        
        # Добавляем месяц в список обработанных
        parsed_data['months'].append({
            'key': month_key,
            'year': year,
            'month': month
        })
        
        try:
            # Читаем файл с правильной кодировкой
            with open(file_path, 'rb') as f:
                content = f.read()
                
            # Размер файла и содержимое для отладки
            file_size = os.path.getsize(file_path)
            print(f"Размер файла: {file_size} байт")
            print(f"Первые 100 байт файла: {content[:100]}")
            
            # Пробуем все возможные кодировки
            for encoding in ['cp1251', 'utf-8', 'windows-1252', 'latin-1']:
                try:
                    # Попытка преобразовать в строку
                    xml_str = content.decode(encoding)
                    
                    # Преобразуем в ElementTree
                    root = ET.fromstring(xml_str)
                    
                    # Если успешно, используем эту кодировку
                    print(f"Успешно распознан файл с кодировкой: {encoding}")
                    break
                except Exception as e:
                    print(f"Ошибка при чтении с кодировкой {encoding}: {e}")
                    continue
            else:
                print(f"Не удалось распознать файл с известными кодировками.")
                continue
            
            # Находим все элементы partner
            partners = root.findall('./partner')
            
            print(f"Найдено {len(partners)} партнеров в файле")
            
            # Если не нашли, попробуем другой путь
            if not partners:
                partners = root.findall('partner')
                print(f"Повторный поиск: найдено {len(partners)} партнеров")
            
            # Обрабатываем каждого партнера
            for partner in partners:
                # Получаем имя
                name_elem = partner.find('name')
                if name_elem is None or name_elem.text is None:
                    print("Пропускаем партнера без имени")
                    continue
                    
                name = name_elem.text.strip()
                
                # Получаем город
                city_elem = partner.find('city')
                city = city_elem.text.strip() if city_elem is not None and city_elem.text else "Не указан"
                
                # Выводим для отладки
                print(f"Обработка партнера: '{name}', город: '{city}'")
                
                # Если это новый партнер, создаем запись
                if name not in parsed_data['partners']:
                    parsed_data['partners'][name] = {
                        'name': name,
                        'city': city,
                        'free_data': {},
                        'paid_data': {}
                    }
                
                # Получаем данные о льготных подписках
                free_amount_elem = partner.find('free_amount')
                free_amount = 0
                if free_amount_elem is not None and free_amount_elem.text:
                    try:
                        free_amount = int(free_amount_elem.text.strip())
                    except ValueError:
                        print(f"Ошибка преобразования free_amount: '{free_amount_elem.text}'")
                
                # Получаем данные о платных подписках
                paid_amount_elem = partner.find('paid_amount')
                paid_amount = 0
                if paid_amount_elem is not None and paid_amount_elem.text:
                    try:
                        paid_amount = int(paid_amount_elem.text.strip())
                    except ValueError:
                        print(f"Ошибка преобразования paid_amount: '{paid_amount_elem.text}'")
                
                # Сохраняем данные в структуру
                parsed_data['partners'][name]['free_data'][month_key] = free_amount
                parsed_data['partners'][name]['paid_data'][month_key] = paid_amount
                
                # Выводим для отладки
                print(f"Сохранены данные для {name}: free_amount={free_amount}, paid_amount={paid_amount}")
                
            print(f"Успешно обработан файл за {month:02d}.{year}, добавлено {len(partners)} партнеров")
                
        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {e}")
    
    # Итоговая статистика
    partners_count = len(parsed_data['partners'])
    months_count = len(parsed_data['months'])
    print(f"Итого обработано: {partners_count} партнеров за {months_count} месяцев")
    
    # Выведем первые 5 партнеров для проверки
    partner_sample = list(parsed_data['partners'].items())[:5]
    for name, data in partner_sample:
        print(f"Пример данных - Партнер: {name}")
        print(f"  Город: {data['city']}")
        print(f"  Льготные: {data['free_data']}")
        print(f"  Платные: {data['paid_data']}")
    
    return parsed_data