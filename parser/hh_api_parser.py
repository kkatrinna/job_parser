import requests
import time
import logging
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HHAPIParser:

    API_URL = "https://api.hh.ru/vacancies"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'python-requests/2.31.0',
            'Accept': 'application/json',
        })

    def search_vacancies(self, query, city=None, max_pages=3):

        all_vacancies = []
        page = 0

        area_id = self._get_city_id(city) if city else 1

        logger.info(f"Поиск: '{query}', город ID: {area_id}, страниц: {max_pages}")

        while page < max_pages:
            try:
                params = {
                    'text': query,
                    'area': area_id,
                    'page': page,
                    'per_page': 20,
                    'order_by': 'publication_time',
                    'period': 30,
                }

                logger.info(f"Запрос API страницы {page + 1} для '{query}'")

                time.sleep(random.uniform(1, 2))

                response = self.session.get(self.API_URL, params=params, timeout=10)

                if response.status_code != 200:
                    logger.error(f"Ошибка API: {response.status_code}")
                    logger.error(f"URL: {response.url}")
                    logger.error(f"Ответ: {response.text[:200]}")
                    break

                data = response.json()

                if 'items' not in data:
                    logger.error("Нет поля 'items' в ответе")
                    break

                items = data.get('items', [])
                logger.info(f"Найдено вакансий на странице: {len(items)}")

                for item in items:
                    vacancy = self._parse_api_vacancy(item)
                    if vacancy:
                        all_vacancies.append(vacancy)

                pages = data.get('pages', 1)
                if page >= pages - 1:
                    logger.info("Достигнута последняя страница")
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка сети: {e}")
                break
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                break

        logger.info(f"Всего получено вакансий: {len(all_vacancies)}")
        return all_vacancies

    def _parse_api_vacancy(self, item):
        try:
            if not item.get('name'):
                return None

            vacancy = {
                'title': item.get('name', ''),
                'company': 'Не указано',
                'salary': 'Не указана',
                'city': 'Не указан',
                'experience': 'Не указан',
                'url': item.get('alternate_url', ''),
                'description': '',
                'published_at': datetime.now()
            }

            employer = item.get('employer', {})
            if employer:
                vacancy['company'] = employer.get('name', 'Не указано')

            area = item.get('area', {})
            if area:
                vacancy['city'] = area.get('name', 'Не указан')

            salary = item.get('salary')
            if salary and isinstance(salary, dict):
                salary_from = salary.get('from')
                salary_to = salary.get('to')
                currency = salary.get('currency', 'руб')

                if salary_from and salary_to:
                    vacancy['salary'] = f"{salary_from} - {salary_to} {currency}"
                elif salary_from:
                    vacancy['salary'] = f"от {salary_from} {currency}"
                elif salary_to:
                    vacancy['salary'] = f"до {salary_to} {currency}"
                else:
                    vacancy['salary'] = 'Не указана'

            experience = item.get('experience', {})
            if experience:
                vacancy['experience'] = experience.get('name', 'Не указан')

            snippet = item.get('snippet', {})
            if snippet:
                requirement = snippet.get('requirement', '')
                responsibility = snippet.get('responsibility', '')
                if requirement or responsibility:
                    vacancy['description'] = f"{requirement} {responsibility}".strip()

            published = item.get('published_at')
            if published:
                try:
                    vacancy['published_at'] = datetime.fromisoformat(published.replace('+0300', '+03:00'))
                except:
                    pass

            return vacancy

        except Exception as e:
            logger.error(f"Ошибка парсинга вакансии: {e}")
            return None

    def _get_city_id(self, city_name):

        if not city_name:
            return 1
        cities = {
            'москва': 1,
            'санкт-петербург': 2,
            'спб': 2,
            'екатеринбург': 3,
            'новосибирск': 4,
            'казань': 88,
            'нижний новгород': 66,
            'ростов-на-дону': 76,
            'самара': 78,
            'уфа': 99,
            'краснодар': 53,
            'воронеж': 26,
            'пермь': 72,
            'волгоград': 24,
            'челябинск': 104,
            'омск': 68,
            'тюмень': 95,
        }

        city_lower = city_name.lower().strip()
        return cities.get(city_lower, 1)