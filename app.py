from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import os
import tempfile
import shutil
import uuid
from datetime import datetime
from modules.downloader import download_xml_files
from modules.parser import parse_xml_data
from modules.excel_generator import generate_excel_files

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# Создаем постоянную директорию для хранения файлов
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Функция для создания уникальной директории пользователя
def get_user_temp_dir():
    # Если у пользователя еще нет ID сессии, создаем новый
    if 'user_temp_dir' not in session:
        session['user_temp_dir'] = str(uuid.uuid4())
    
    # Создаем директорию для пользователя
    user_dir = os.path.join(UPLOAD_FOLDER, session['user_temp_dir'])
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

@app.route('/', methods=['GET'])
def index():
    current_year = datetime.now().year
    years = list(range(2024, current_year + 1))
    return render_template('index.html', years=years)

@app.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        # Создаем временную директорию для пользователя
        temp_dir = get_user_temp_dir()
        
        # Получаем параметры из формы
        year = request.form.get('year')
        period_type = request.form.get('period_type')
        
        # Получаем учетные данные
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверяем, требуются ли учетные данные
        use_local_files = request.form.get('use_local_files') == 'true'
        if not use_local_files and (not username or not password):
            return render_template('error.html', 
                                message="Для получения данных необходимо указать логин и пароль от сайта 1С.")
        
        # Определяем список месяцев для обработки
        months = get_months_from_period(period_type, request.form.getlist('custom_months'))
        if not months:
            return render_template('error.html', 
                                message="Не выбраны месяцы для отчета. Пожалуйста, выберите хотя бы один месяц.")
        
        # Определяем тип отчета
        report_type = request.form.get('report_type')
        
        # Получаем XML-файлы
        if use_local_files:
            xml_files = create_test_xml_files(year, months, temp_dir)
        else:
            xml_files = download_xml_files(year, months, temp_dir, username, password)
        
        # Проверяем, загрузились ли файлы
        if not xml_files:
            return render_template('error.html', 
                                message="Не удалось загрузить XML файлы. Проверьте правильность учетных данных и подключение к интернету.")
        
        # Парсим данные
        parsed_data = parse_xml_data(xml_files)
        
        # Проверяем, что данные успешно извлечены
        if not parsed_data['partners']:
            return render_template('error.html', 
                                message="Не удалось извлечь данные партнеров из XML файлов. Возможно, формат файлов изменился.")
        
        # Генерируем Excel-файлы
        excel_files = []
        try:
            if report_type in ['free', 'both']:
                free_excel = generate_excel_files(parsed_data, 'free', year, months, temp_dir)
                excel_files.append({'name': 'Льготные 1C:ИТС', 'path': free_excel})
            
            if report_type in ['paid', 'both']:
                paid_excel = generate_excel_files(parsed_data, 'paid', year, months, temp_dir)
                excel_files.append({'name': 'Платные 1C:ИТС', 'path': paid_excel})
        except Exception as e:
            return render_template('error.html', 
                                message=f"Произошла ошибка при создании Excel-файлов: {str(e)}")
        
        # Проверяем, что файлы существуют
        for file_info in excel_files:
            if not os.path.exists(file_info['path']):
                return render_template('error.html', 
                                    message=f"Не удалось создать файл отчета: {file_info['name']}")
        
        # Сохраняем пути к файлам в сессии
        session['excel_files'] = excel_files
        
        return render_template('result.html', excel_files=excel_files)
    
    except Exception as e:
        return render_template('error.html', 
                            message=f"Произошла непредвиденная ошибка: {str(e)}")

def get_months_from_period(period_type, custom_months=None):
    """Получение списка месяцев на основе выбранного периода"""
    if period_type == 'year':
        return list(range(1, 13))
    elif period_type == 'q1':
        return [1, 2, 3]
    elif period_type == 'q2':
        return [4, 5, 6]
    elif period_type == 'q3':
        return [7, 8, 9]
    elif period_type == 'q4':
        return [10, 11, 12]
    elif period_type == 'custom' and custom_months:
        return [int(month) for month in custom_months]
    return []

@app.route('/download/<int:file_index>')
def download_file(file_index):
    excel_files = session.get('excel_files', [])
    
    if 0 <= file_index < len(excel_files):
        file_info = excel_files[file_index]
        file_path = file_info['path']
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            return render_template('error.html',
                                message="Файл не найден. Возможно, он был удален или истек срок его хранения."), 404
        
        file_name = f"{file_info['name']}.xlsx"
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=file_name)
    
    return redirect(url_for('index'))

def create_test_xml_files(year, months, temp_dir):
    """Создает тестовые XML файлы для указанного года и месяцев"""
    sample_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<partners>
	<partner>
		<place>1</place>
		<region>Кыргызстан</region>
		<city>Бишкек</city>
		<name>1С-Като Экономикс</name>
		<all_subs>2343 (+3.4%)</all_subs>
		<all_amount>2343</all_amount>
		<all_change>3.4</all_change>
		<free_subs>18 (+5.88%)</free_subs>
		<free_amount>18</free_amount>
		<free_change>5.88</free_change>
		<paid_subs>2325 (+3.38%)</paid_subs>
		<paid_amount>2325</paid_amount>
		<paid_change>3.38</paid_change>
		<perf_subs>1</perf_subs>
		<perf_amount>1</perf_amount>
		<perf_change>0</perf_change>
		<movement></movement>
		<duo_subs>0</duo_subs>
		<duo_amount>0</duo_amount>
		<otchetnost>0</otchetnost>
		<paid_drop>9.44%</paid_drop>
		<free_drop>69.91%</free_drop>
		<share>64.56%</share>
		<share_change>-1.62%</share_change>
		<status></status>
		<in_order>Да</in_order>
		<perf_ratio>Да</perf_ratio>
	</partner>
	<partner>
		<place>2</place>
		<region>Кыргызстан</region>
		<city>Бишкек</city>
		<name>ЛИСТ Кей Джи</name>
		<all_subs>212 (+7.07%)</all_subs>
		<all_amount>212</all_amount>
		<all_change>7.07</all_change>
		<free_subs>24 (-4%)</free_subs>
		<free_amount>24</free_amount>
		<free_change>-4</free_change>
		<paid_subs>188 (+8.67%)</paid_subs>
		<paid_amount>188</paid_amount>
		<paid_change>8.67</paid_change>
		<perf_subs>1</perf_subs>
		<perf_amount>1</perf_amount>
		<perf_change>0</perf_change>
		<movement></movement>
		<duo_subs>0</duo_subs>
		<duo_amount>0</duo_amount>
		<otchetnost>0</otchetnost>
		<paid_drop></paid_drop>
		<free_drop>15.85%</free_drop>
		<share>5.84%</share>
		<share_change>1.92%</share_change>
		<status></status>
		<in_order>Нет</in_order>
		<perf_ratio>Да</perf_ratio>
	</partner>
</partners>"""
    
    # Создаем файлы для каждого месяца
    test_files = []
    for month in months:
        filename = f"export_{year}_{month:02d}.xml"
        file_path = os.path.join(temp_dir, filename)
        
        # Записываем содержимое в файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_xml_content)
        
        # Добавляем информацию о файле
        test_files.append({
            'path': file_path,
            'year': int(year),
            'month': month
        })
    
    return test_files

# Очистка старых временных файлов (запускается периодически)
@app.before_request
def cleanup_old_temp_dirs():
    try:
        # Очищаем только старые директории (не текущую сессию)
        if 'user_temp_dir' in session and os.path.exists(UPLOAD_FOLDER):
            current_user_dir = session['user_temp_dir']
            for dir_name in os.listdir(UPLOAD_FOLDER):
                dir_path = os.path.join(UPLOAD_FOLDER, dir_name)
                if dir_name != current_user_dir and os.path.isdir(dir_path):
                    # Проверяем, что директория старше определенного времени
                    dir_age = datetime.now().timestamp() - os.path.getmtime(dir_path)
                    if dir_age > 86400:  # 24 часа в секундах
                        shutil.rmtree(dir_path, ignore_errors=True)
    except Exception:
        # Игнорируем ошибки при очистке
        pass

if __name__ == '__main__':
    app.run(debug=True)