import pandas as pd
import os
from datetime import datetime
from flask import current_app


def save_to_excel(vacancies, filename=None):
    if not vacancies:
        return None

    download_folder = current_app.config['DOWNLOAD_FOLDER']
    os.makedirs(download_folder, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'vacancies_{timestamp}.xlsx'

    filepath = os.path.join(download_folder, filename)

    df = pd.DataFrame(vacancies)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Вакансии', index=False)

        worksheet = writer.sheets['Вакансии']
        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.column_dimensions[chr(65 + col_idx)].width = min(column_width + 2, 50)

    return filepath


def save_to_csv(vacancies, filename=None):
    if not vacancies:
        return None

    download_folder = current_app.config['DOWNLOAD_FOLDER']
    os.makedirs(download_folder, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'vacancies_{timestamp}.csv'

    filepath = os.path.join(download_folder, filename)

    df = pd.DataFrame(vacancies)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    return filepath


def format_salary(salary_str):
    if not salary_str or salary_str == 'Не указана':
        return 'Договорная'

    salary_str = ' '.join(salary_str.split())
    return salary_str


def extract_salary_range(salary_str):
    if not salary_str or salary_str == 'Не указана':
        return (None, None, None)

    import re

    patterns = [
        r'от (\d[\d\s]*)',  # от 100000
        r'до (\d[\d\s]*)',  # до 100000
        r'(\d[\d\s]*)[-–—](\d[\d\s]*)',  # 100000-150000
    ]

    salary_str = salary_str.replace(' ', '').replace('\xa0', '')

    for pattern in patterns:
        match = re.search(pattern, salary_str)
        if match:
            if 'от' in pattern:
                min_sal = int(match.group(1))
                return (min_sal, None, 'руб')
            elif 'до' in pattern:
                max_sal = int(match.group(1))
                return (None, max_sal, 'руб')
            else:
                min_sal = int(match.group(1))
                max_sal = int(match.group(2))
                return (min_sal, max_sal, 'руб')

    return (None, None, None)