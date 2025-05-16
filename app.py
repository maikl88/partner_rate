from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import os
from datetime import datetime
import tempfile
import shutil
from werkzeug.utils import secure_filename
from modules.downloader import download_xml_files
from modules.parser import parse_xml_data
from modules.excel_generator import generate_excel_files

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Для использования session

# Создаем временную директорию для хранения файлов
TEMP_DIR = tempfile.mkdtemp()

@app.route('/', methods=['GET'])
def index():
    current_year = datetime.now().year
    years = list(range(2024, current_year + 1))
    return render_template('index.html', years=years)

@app.route('/generate_report', methods=['POST'])
def generate_report():
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
    
    print(f"Начало генерации отчета. Год: {year}, тип периода: {period_type}")
    
    # Определяем список месяцев для обработки
    months = []
    if period_type == 'year':
        months = list(range(1, 13))
    elif period_type == 'q1':
        months = [1, 2, 3]
    elif period_type == 'q2':
        months = [4, 5, 6]
    elif period_type == 'q3':
        months = [7, 8, 9]
    elif period_type == 'q4':
        months = [10, 11, 12]
    elif period_type == 'custom':
        # Получаем выбранные месяцы из мультиселекта
        months = request.form.getlist('custom_months')
        if not months:
            return render_template('error.html', 
                                 message="Не выбраны месяцы для отчета. Пожалуйста, выберите хотя бы один месяц.")
        months = [int(month) for month in months]
    
    report_type = request.form.get('report_type')
    print(f"Тип отчета: {report_type}, месяцы: {months}")
    
    # Определяем источник данных
    if use_local_files:
        # Используем локальные файлы для тестирования
        xml_files = create_test_xml_files(year, months, TEMP_DIR)
    else:
        # Загружаем файлы с сайта, используя авторизацию
        xml_files = download_xml_files(year, months, TEMP_DIR, username, password)
    
    # Проверяем, загрузились ли файлы
    if not xml_files:
        return render_template('error.html', 
                              message="Не удалось загрузить XML файлы. Проверьте правильность учетных данных и подключение к интернету.")
    
    print(f"Загружено {len(xml_files)} XML-файлов")
    
    # Парсим данные из XML
    parsed_data = parse_xml_data(xml_files)
    
    # Проверяем, что данные успешно извлечены
    if not parsed_data['partners']:
        return render_template('error.html', 
                              message="Не удалось извлечь данные партнеров из XML файлов. Возможно, формат файлов изменился.")
    
    print(f"Извлечены данные {len(parsed_data['partners'])} партнеров за {len(parsed_data['months'])} месяцев")
    
    # Генерируем Excel-файлы
    excel_files = []
    try:
        if report_type in ['free', 'both']:
            free_excel = generate_excel_files(parsed_data, 'free', year, months, TEMP_DIR)
            excel_files.append({'name': 'Льготные 1C:ИТС', 'path': free_excel})
        
        if report_type in ['paid', 'both']:
            paid_excel = generate_excel_files(parsed_data, 'paid', year, months, TEMP_DIR)
            excel_files.append({'name': 'Платные 1C:ИТС', 'path': paid_excel})
    except Exception as e:
        print(f"Ошибка при создании Excel-файлов: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', 
                             message=f"Произошла ошибка при создании Excel-файлов: {e}")
    
    # Сохраняем пути к файлам в сессии для последующей загрузки
    session['excel_files'] = excel_files
    
    print(f"Созданы Excel-файлы: {[f['name'] for f in excel_files]}")
    
    return render_template('result.html', excel_files=excel_files)

@app.route('/download/<int:file_index>')
def download_file(file_index):
    excel_files = session.get('excel_files', [])
    
    if 0 <= file_index < len(excel_files):
        file_info = excel_files[file_index]
        file_name = f"{file_info['name']}.xlsx"
        return send_file(file_info['path'], 
                        as_attachment=True, 
                        download_name=file_name)
    
    return redirect(url_for('index'))

@app.route('/upload_xml', methods=['POST'])
def upload_xml():
    # Проверяем, что файлы были загружены
    if 'xml_files[]' not in request.files:
        return jsonify({'error': 'Файлы не были загружены'}), 400
    
    files = request.files.getlist('xml_files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'Файлы не выбраны'}), 400
    
    # Создаем временную директорию, если она еще не существует
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        if file and file.filename.endswith('.xml'):
            # Получаем информацию о месяце и годе из имени файла
            filename = secure_filename(file.filename)
            file_path = os.path.join(TEMP_DIR, filename)
            
            # Сохраняем файл
            file.save(file_path)
            
            # Пытаемся извлечь месяц и год из имени файла
            try:
                parts = filename.replace('.xml', '').split('_')
                year = int(parts[-2])
                month = int(parts[-1])
            except (ValueError, IndexError):
                # Если не удалось извлечь, используем текущую дату
                now = datetime.now()
                year = now.year
                month = now.month
            
            uploaded_files.append({
                'path': file_path,
                'year': year,
                'month': month
            })
    
    # Сохраняем информацию о загруженных файлах в сессии
    session['uploaded_files'] = uploaded_files
    
    return jsonify({
        'success': True,
        'message': f'Загружено {len(uploaded_files)} файлов',
        'files': [{'name': os.path.basename(f['path']), 'year': f['year'], 'month': f['month']} for f in uploaded_files]
    })

def create_test_xml_files(year, months, temp_dir):
    """
    Создает тестовые XML файлы на основе шаблона для указанного года и месяцев
    
    Args:
        year (str): Год для создания данных
        months (list): Список месяцев
        temp_dir (str): Директория для сохранения файлов
    
    Returns:
        list: Список словарей с информацией о созданных файлах
    """
    # Пример XML-данных (на основе предоставленного вами файла)
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
	<partner>
		<place>3</place>
		<region>Кыргызстан</region>
		<city>Бишкек</city>
		<name>ARKAD Pro</name>
		<all_subs>170 (+3.66%)</all_subs>
		<all_amount>170</all_amount>
		<all_change>3.66</all_change>
		<free_subs>15 (-16.67%)</free_subs>
		<free_amount>15</free_amount>
		<free_change>-16.67</free_change>
		<paid_subs>155 (+6.16%)</paid_subs>
		<paid_amount>155</paid_amount>
		<paid_change>6.16</paid_change>
		<perf_subs>1</perf_subs>
		<perf_amount>1</perf_amount>
		<perf_change>0</perf_change>
		<movement></movement>
		<duo_subs>0</duo_subs>
		<duo_amount>0</duo_amount>
		<otchetnost>0</otchetnost>
		<paid_drop></paid_drop>
		<free_drop>14.55%</free_drop>
		<share>4.68%</share>
		<share_change>-1.47%</share_change>
		<status></status>
		<in_order>Нет</in_order>
		<perf_ratio>Да</perf_ratio>
	</partner>
	<partner>
		<place>4</place>
		<region>Кыргызстан</region>
		<city>Ош</city>
		<name>1С:Франчайзинг. Сервис.kg</name>
		<all_subs>130 (+9.24%)</all_subs>
		<all_amount>130</all_amount>
		<all_change>9.24</all_change>
		<free_subs>28 (+21.74%)</free_subs>
		<free_amount>28</free_amount>
		<free_change>21.74</free_change>
		<paid_subs>102 (+6.25%)</paid_subs>
		<paid_amount>102</paid_amount>
		<paid_change>6.25</paid_change>
		<perf_subs>1</perf_subs>
		<perf_amount>1</perf_amount>
		<perf_change>0</perf_change>
		<movement></movement>
		<duo_subs>0</duo_subs>
		<duo_amount>0</duo_amount>
		<otchetnost>0</otchetnost>
		<paid_drop>20%</paid_drop>
		<free_drop>54.29%</free_drop>
		<share>3.58%</share>
		<share_change>3.77%</share_change>
		<status></status>
		<in_order>Да</in_order>
		<perf_ratio>Да</perf_ratio>
	</partner>
	<partner>
		<place>5</place>
		<region>Кыргызстан</region>
		<city>Бишкек</city>
		<name>0.1 АДВИЦ</name>
		<all_subs>86 (+4.88%)</all_subs>
		<all_amount>86</all_amount>
		<all_change>4.88</all_change>
		<free_subs>5</free_subs>
		<free_amount>5</free_amount>
		<free_change>0</free_change>
		<paid_subs>81 (+5.19%)</paid_subs>
		<paid_amount>81</paid_amount>
		<paid_change>5.19</paid_change>
		<perf_subs>1</perf_subs>
		<perf_amount>1</perf_amount>
		<perf_change>0</perf_change>
		<movement></movement>
		<duo_subs>0</duo_subs>
		<duo_amount>0</duo_amount>
		<otchetnost>0</otchetnost>
		<paid_drop></paid_drop>
		<free_drop>8.57%</free_drop>
		<share>2.37%</share>
		<share_change>0%</share_change>
		<status></status>
		<in_order>Нет</in_order>
		<perf_ratio>Да</perf_ratio>
	</partner>
</partners>"""
    
    # Создаем файлы для каждого месяца
    test_files = []
    for month in months:
        # Создаем имя файла и путь
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
        
        print(f"Создан тестовый XML-файл для {month:02d}.{year}: {file_path}")
    
    print(f"Всего создано тестовых файлов: {len(test_files)}")
    return test_files

@app.route('/progress')
def progress():
    # Для индикации прогресса (если нужно)
    progress_status = session.get('progress_status', 'Ожидание...')
    return jsonify({'status': progress_status})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Страница не найдена"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', message="Внутренняя ошибка сервера. Пожалуйста, попробуйте позже."), 500

# Очистка временных файлов при завершении
@app.teardown_appcontext
def cleanup_temp_files(exception=None):
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
    except Exception as e:
        print(f"Ошибка при очистке временных файлов: {e}")

if __name__ == '__main__':
    app.run(debug=True)