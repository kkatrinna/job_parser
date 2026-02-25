from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, flash, abort
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange
import os
from datetime import datetime
import threading
import time
import traceback

from parser.hh_api_parser import HHAPIParser as HHParser
from parser.models import db, SearchQuery, Job
from parser.utils import save_to_excel, save_to_csv, format_salary
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

try:
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            print(f" Папка для БД создана/проверена: {db_dir}")
        else:
            print(f" База данных будет создана в текущей директории: {db_path}")
except Exception as e:
    print(f" Не удалось создать папку для БД: {e}")
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(data_dir, "jobs.db")}'
    print(f" Используем запасной путь БД: {app.config['SQLALCHEMY_DATABASE_URI']}")


class SearchForm(FlaskForm):
    query = StringField('Профессия или ключевые слова', validators=[DataRequired()])
    city = StringField('Город', validators=[Optional()])
    max_pages = IntegerField('Максимум страниц', default=3,
                             validators=[NumberRange(min=1, max=10)])
    format = SelectField('Формат файла', choices=[('excel', 'Excel'), ('csv', 'CSV')])
    submit = SubmitField('Найти вакансии')


def get_object_or_404(model, id):
    obj = db.session.get(model, id)
    if obj is None:
        abort(404, description=f"{model.__name__} не найден")
    return obj


class ParserThread(threading.Thread):
    def __init__(self, query, city, max_pages, search_id):
        threading.Thread.__init__(self)
        self.query = query
        self.city = city
        self.max_pages = max_pages
        self.search_id = search_id
        self.result = None

    def run(self):
        print(f"\n{'=' * 60}")
        print(f" ЗАПУСК ПАРСЕРА В ФОНЕ")
        print(f"   Запрос: {self.query}")
        print(f"   Город: {self.city or 'Москва'}")
        print(f"   Страниц: {self.max_pages}")
        print(f"   ID поиска: {self.search_id}")
        print(f"   Время: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'=' * 60}")

        try:
            parser = HHParser()
            print(f" Парсер создан")

            print(f" Начинаем поиск вакансий...")
            vacancies = parser.search_vacancies(self.query, self.city, self.max_pages)

            print(f" Найдено вакансий: {len(vacancies)}")

            if vacancies:
                print(f" Пример вакансии:")
                sample = vacancies[0]
                print(f"   Название: {sample.get('title', 'Н/Д')}")
                print(f"   Компания: {sample.get('company', 'Н/Д')}")
                print(f"   Зарплата: {sample.get('salary', 'Н/Д')}")
                print(f"   Город: {sample.get('city', 'Н/Д')}")
            else:
                print(f" Вакансии не найдены!")
                if self.city:
                    print(f" Пробуем поиск в Москве...")
                    vacancies = parser.search_vacancies(self.query, "Москва", self.max_pages)
                    print(f" Найдено вакансий в Москве: {len(vacancies)}")

            if vacancies:
                with app.app_context():
                    print(f" Сохраняем в базу данных...")
                    search = db.session.get(SearchQuery, self.search_id)

                    if not search:
                        print(f" Ошибка: поиск с ID {self.search_id} не найден в БД")
                        return

                    print(f" Найден поисковый запрос: {search.query}")

                    saved_count = 0
                    for i, vac in enumerate(vacancies, 1):
                        try:
                            title = vac.get('title', '')
                            if not title or len(title.strip()) < 2:
                                print(f"    Пропущена вакансия {i}: нет названия")
                                continue

                            job = Job(
                                title=title[:200],
                                company=vac.get('company', 'Не указано')[:200],
                                salary=vac.get('salary', 'Не указана')[:100],
                                city=vac.get('city', 'Не указан')[:100],
                                experience=vac.get('experience', '')[:100],
                                url=vac.get('url', '')[:500] if vac.get('url') else '',
                                published_at=vac.get('published_at', datetime.now()),
                                description=str(vac.get('description', ''))[:1000] if vac.get('description') else '',
                                search_query_id=search.id
                            )

                            existing = Job.query.filter_by(url=job.url).first()
                            if existing:
                                print(f"    Вакансия {i} уже существует в БД, пропускаем")
                                continue

                            db.session.add(job)
                            saved_count += 1

                            if saved_count % 5 == 0:
                                print(f"    Сохранено {saved_count} вакансий...")
                                db.session.flush()

                        except Exception as e:
                            print(f"    Ошибка при сохранении вакансии {i}: {e}")
                            continue
                    search.results_count = saved_count

                    try:
                        db.session.commit()
                        print(f" УСПЕШНО сохранено {saved_count} вакансий в БД")
                    except Exception as e:
                        db.session.rollback()
                        print(f" Ошибка при коммите в БД: {e}")

                    self.result = vacancies
            else:
                print(f" Нет вакансий для сохранения")

        except Exception as e:
            print(f" КРИТИЧЕСКАЯ ОШИБКА В ПАРСЕРЕ: {e}")
            import traceback
            traceback.print_exc()
            self.result = []

        print(f"{'=' * 60}\n")

with app.app_context():
    try:
        db.create_all()
        print(" Таблицы базы данных созданы успешно")

        try:
            test_query = db.session.execute(db.select(SearchQuery)).first()
            print(" Соединение с БД работает")
        except Exception as e:
            print(f"\ Предупреждение при проверке БД: {e}")
    except Exception as e:
        print(f" Ошибка при создании таблиц: {e}")
        traceback.print_exc()


@app.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()

    if form.validate_on_submit():
        try:
            print(f"\n Новый поисковый запрос: {form.query.data}")

            search = SearchQuery(
                query=form.query.data,
                city=form.city.data or 'Москва',
            )
            db.session.add(search)
            db.session.commit()
            print(f" Поисковый запрос сохранен с ID: {search.id}")

            thread = ParserThread(
                form.query.data,
                form.city.data,
                form.max_pages.data,
                search.id
            )
            thread.daemon = True
            thread.start()

            flash(f'🔍 Поиск по запросу "{form.query.data}" начат! Результаты появятся через несколько секунд.',
                  'success')
            return redirect(url_for('results', search_id=search.id))

        except Exception as e:
            db.session.rollback()
            error_msg = f'Ошибка при сохранении запроса: {str(e)}'
            flash(error_msg, 'danger')
            print(f" {error_msg}")
            traceback.print_exc()

    return render_template('index.html', form=form)


@app.route('/results/<int:search_id>')
def results(search_id):
    print(f"\n Загрузка результатов для поиска ID: {search_id}")

    try:
        search = get_object_or_404(SearchQuery, search_id)
        print(f" Найден поиск: '{search.query}', создан: {search.created_at}")

        jobs = Job.query.filter_by(search_query_id=search_id).all()
        print(f" Загружено вакансий из БД: {len(jobs)}")

        if not jobs and search.created_at:
            time_diff = datetime.now() - search.created_at
            if time_diff.seconds < 30:
                flash(' Поиск выполняется. Пожалуйста, подождите...', 'info')
                return render_template('loading.html', search=search)

        stats = {
            'total': len(jobs),
            'with_salary': sum(1 for j in jobs if j.salary and j.salary != 'Не указана'),
            'cities': len(set(j.city for j in jobs if j.city))
        }
        print(f" Статистика: {stats}")

        return render_template('results.html',
                               search=search,
                               jobs=jobs,
                               stats=stats,
                               format_salary=format_salary)

    except Exception as e:
        error_msg = f'Ошибка при загрузке результатов: {str(e)}'
        flash(error_msg, 'danger')
        print(f" {error_msg}")
        traceback.print_exc()
        return redirect(url_for('index'))


@app.route('/download/<int:search_id>')
def download(search_id):
    try:
        format_type = request.args.get('format', 'excel')
        print(f"\n Скачивание результатов для поиска ID: {search_id}, формат: {format_type}")

        search = get_object_or_404(SearchQuery, search_id)

        jobs = Job.query.filter_by(search_query_id=search_id).all()
        print(f" Найдено {len(jobs)} вакансий для скачивания")

        if not jobs:
            flash('Нет данных для скачивания', 'warning')
            return redirect(url_for('results', search_id=search_id))

        vacancies = [job.to_dict() for job in jobs]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == 'excel':
            filepath = save_to_excel(vacancies)
            filename = f'vacancies_{search.query}_{timestamp}.xlsx'
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            filepath = save_to_csv(vacancies)
            filename = f'vacancies_{search.query}_{timestamp}.csv'
            mimetype = 'text/csv'

        if filepath and os.path.exists(filepath):
            print(f" Файл создан: {filepath}")
            return send_file(filepath, as_attachment=True,
                             download_name=filename, mimetype=mimetype)
        else:
            flash('Ошибка при создании файла', 'danger')
            return redirect(url_for('results', search_id=search_id))

    except Exception as e:
        error_msg = f'Ошибка при скачивании: {str(e)}'
        flash(error_msg, 'danger')
        print(f" {error_msg}")
        traceback.print_exc()
        return redirect(url_for('results', search_id=search_id))


@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        query = data.get('query')
        city = data.get('city')
        max_pages = data.get('max_pages', 3)

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        print(f"\n API запрос: {query}, город: {city or 'Москва'}")

        parser = HHParser()
        vacancies = parser.search_vacancies(query, city, max_pages)

        print(f" API найдено вакансий: {len(vacancies)}")

        return jsonify({
            'success': True,
            'count': len(vacancies),
            'vacancies': vacancies
        })

    except Exception as e:
        print(f" Ошибка API: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/history')
def history():
    try:
        from sqlalchemy import desc

        result = db.session.execute(
            db.select(SearchQuery).order_by(desc(SearchQuery.created_at))
        )
        searches = result.scalars().all()

        print(f"\n Загружена история: {len(searches)} записей")
        return render_template('history.html', searches=searches)

    except Exception as e:
        error_msg = f'Ошибка при загрузке истории: {str(e)}'
        flash(error_msg, 'danger')
        print(f" {error_msg}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')


@app.errorhandler(404)
def not_found_error(error):
    flash('Страница не найдена', 'warning')
    return redirect(url_for('index'))


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    flash('Внутренняя ошибка сервера', 'danger')
    print(f" Внутренняя ошибка сервера: {error}")
    traceback.print_exc()
    return redirect(url_for('index'))


@app.context_processor
def utility_processor():
    return {
        'now': datetime.now()
    }


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print(" ЗАПУСК ПРИЛОЖЕНИЯ")
    print("=" * 60)
    print(f" Папка загрузок: {app.config['DOWNLOAD_FOLDER']}")
    print(f"️  База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f" Режим отладки: {app.debug}")
    print("=" * 60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)