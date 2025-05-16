import xml.etree.ElementTree as ET

def parse_xml_data(xml_files):
    """Парсинг данных из XML файлов"""
    # Структура для хранения данных
    parsed_data = {
        'partners': {},
        'months': []
    }
    
    # Сортируем файлы по месяцам
    xml_files.sort(key=lambda x: (x['year'], x['month']))
    
    for file_info in xml_files:
        file_path = file_info['path']
        year = file_info['year']
        month = file_info['month']
        month_key = f"{year}_{month:02d}"
        
        # Добавляем месяц в список обработанных
        parsed_data['months'].append({
            'key': month_key,
            'year': year,
            'month': month
        })
        
        try:
            # Пробуем различные кодировки
            for encoding in ['utf-8', 'cp1251', 'windows-1252', 'latin-1']:
                try:
                    # Читаем файл
                    with open(file_path, 'r', encoding=encoding) as f:
                        xml_content = f.read()
                    
                    # Парсим XML
                    root = ET.fromstring(xml_content)
                    break
                except:
                    continue
            else:
                # Если не удалось распознать кодировку, пропускаем файл
                continue
                
            # Находим всех партнеров
            partners = root.findall('./partner') or root.findall('partner')
            
            # Обрабатываем каждого партнера
            for partner in partners:
                # Получаем имя
                name_elem = partner.find('name')
                if name_elem is None or name_elem.text is None:
                    continue
                
                name = name_elem.text.strip()
                
                # Получаем город
                city_elem = partner.find('city')
                city = city_elem.text.strip() if city_elem is not None and city_elem.text else "Не указан"
                
                # Если это новый партнер, создаем запись
                if name not in parsed_data['partners']:
                    parsed_data['partners'][name] = {
                        'name': name,
                        'city': city,
                        'free_data': {},
                        'paid_data': {}
                    }
                
                # Получаем данные о льготных подписках
                free_amount = 0
                free_elem = partner.find('free_amount')
                if free_elem is not None and free_elem.text:
                    try:
                        free_amount = int(free_elem.text.strip())
                    except ValueError:
                        pass
                
                # Получаем данные о платных подписках
                paid_amount = 0
                paid_elem = partner.find('paid_amount')
                if paid_elem is not None and paid_elem.text:
                    try:
                        paid_amount = int(paid_elem.text.strip())
                    except ValueError:
                        pass
                
                # Сохраняем данные
                parsed_data['partners'][name]['free_data'][month_key] = free_amount
                parsed_data['partners'][name]['paid_data'][month_key] = paid_amount
                
        except Exception:
            continue
    
    return parsed_data