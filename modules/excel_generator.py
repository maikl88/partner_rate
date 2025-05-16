import os
import pandas as pd
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

def generate_excel_files(parsed_data, report_type, year, months, temp_dir):
    """Создание Excel файлов с отчетами"""
    # Определяем тип отчета
    if report_type == 'free':
        file_title = f"Льготные_1C_ИТС_{year}"
        data_key = 'free_data'
        title = "Льготные 1C:ИТС"
    else:  # 'paid'
        file_title = f"Платные_1C_ИТС_{year}"
        data_key = 'paid_data'
        title = "Платные 1C:ИТС"
    
    # Проверяем наличие данных
    if not parsed_data['months'] or not parsed_data['partners']:
        empty_path = os.path.join(temp_dir, f"{file_title}.xlsx")
        
        # Создаем пустой файл
        df = pd.DataFrame({"Сообщение": ["Нет данных для отчета"]})
        df.to_excel(empty_path, index=False, sheet_name="Отчет")
        
        return empty_path
    
    # Сортируем месяцы
    sorted_months = sorted(parsed_data['months'], key=lambda x: (x['year'], x['month']))
    
    # Создаем список колонок основной информации
    columns = ["Номер", "Название", "Город"]
    
    # Создаем данные для таблицы
    rows = []
    for idx, (name, partner_data) in enumerate(parsed_data['partners'].items(), 1):
        row = {
            "Номер": idx,
            "Название": name,
            "Город": partner_data['city']
        }
        
        # Добавляем данные по месяцам
        for i, month_info in enumerate(sorted_months):
            month_key = month_info['key']
            month_name = f"{month_info['month']:02d}.{year}"
            
            # Значение за месяц
            month_value = partner_data[data_key].get(month_key, 0)
            row[month_name] = month_value
            
            # Если есть следующий месяц, добавляем разницу
            if i < len(sorted_months) - 1:
                next_month_info = sorted_months[i+1]
                next_month_key = next_month_info['key']
                next_month_name = f"{next_month_info['month']:02d}.{year}"
                
                next_value = partner_data[data_key].get(next_month_key, 0)
                diff = next_value - month_value
                
                diff_col = f"Разница {month_name}-{next_month_name}"
                row[diff_col] = diff
        
        rows.append(row)
    
    # Формируем полный список колонок с учетом чередования месяцев и разниц
    all_columns = ["Номер", "Название", "Город"]
    
    for i, month_info in enumerate(sorted_months):
        month_name = f"{month_info['month']:02d}.{year}"
        all_columns.append(month_name)
        
        # Добавляем колонку с разницей после месяца (если не последний месяц)
        if i < len(sorted_months) - 1:
            next_month_info = sorted_months[i+1]
            next_month_name = f"{next_month_info['month']:02d}.{year}"
            diff_col = f"Разница {month_name}-{next_month_name}"
            all_columns.append(diff_col)
    
    # Создаем DataFrame
    df = pd.DataFrame(rows)
    
    # Сортируем по последнему месяцу (если есть)
    if sorted_months:
        last_month = f"{sorted_months[-1]['month']:02d}.{year}"
        df = df.sort_values(by=last_month, ascending=False).reset_index(drop=True)
        df['Номер'] = range(1, len(df) + 1)
    
    # Переупорядочиваем колонки
    df = df[all_columns]
    
    # Сохраняем в Excel
    file_path = os.path.join(temp_dir, f"{file_title}.xlsx")
    
    # Создаем Excel с форматированием
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Отчет')
        
        # Получаем объекты книги и листа
        workbook = writer.book
        worksheet = writer.sheets['Отчет']
        
        # Форматируем заголовки
        for col_num, column_title in enumerate(df.columns, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
            
            # Выделяем разницы цветом
            if 'Разница' in column_title:
                cell.fill = PatternFill(start_color='D9EAD3', end_color='D9EAD3', fill_type='solid')
            else:
                cell.fill = PatternFill(start_color='C9DAF8', end_color='C9DAF8', fill_type='solid')
        
        # Форматируем числовые ячейки и разницы
        for row_idx in range(2, len(df) + 2):
            for col_idx, col_name in enumerate(df.columns, 1):
                cell = worksheet.cell(row=row_idx, column=col_idx)
                
                # Форматирование числовых ячеек
                if isinstance(cell.value, (int, float)):
                    cell.alignment = Alignment(horizontal='center')
                    
                    # Выделение положительных/отрицательных значений разницы
                    if 'Разница' in col_name:
                        if cell.value > 0:
                            cell.font = Font(color='006100')  # Зеленый для положительных
                        elif cell.value < 0:
                            cell.font = Font(color='9C0006')  # Красный для отрицательных
        
        # Автоподбор ширины колонок
        for col_num, column in enumerate(df.columns, 1):
            column_letter = get_column_letter(col_num)
            # Устанавливаем базовую ширину
            max_length = max(len(str(column)), 12)
            worksheet.column_dimensions[column_letter].width = max_length + 2
    
    return file_path