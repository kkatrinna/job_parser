import requests
import time
import re
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime
from urllib.parse import quote, urlencode
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HHParser:
    BASE_URL = "https://hh.ru"
    SEARCH_URL = "https://hh.ru/search/vacancy"

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers'
        })

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
            'ижевск': 44,
            'барнаул': 10,
            'иркутск': 46,
            'хабаровск': 30,
            'ярославль': 16,
            'владивосток': 22,
            'красноярск': 54,
            'саратов': 79,
            'рязань': 77,
            'липецк': 61,
            'пенза': 71,
            'киров': 50,
            'тула': 93,
            'чебоксары': 103,
            'калининград': 22,
            'мурманск': 64,
            'архангельск': 9,
            'владимир': 23,
            'смоленск': 83,
            'тверь': 90,
            'белгород': 13,
            'курск': 59,
            'орёл': 69,
            'псков': 73,
            'новгород': 67,
            'кострома': 56,
            'иваново': 43,
            'брянск': 19,
            'калуга': 48,
            'магадан': 62,
            'петрозаводск': 31,
            'сыктывкар': 86,
            'нальчик': 65,
            'грозный': 34,
            'махачкала': 63,
            'ставрополь': 85,
            'астрахань': 11,
            'элиста': 38,
            'ростов': 76,
            'севастополь': 119,
            'симферополь': 118,
            'донецк': 107,
            'луганск': 108,
            'запорожье': 109,
            'херсон': 110,
        }

        city_lower = city_name.lower().strip()
        return cities.get(city_lower, 1)

    def search_vacancies(self, query, city=None, max_pages=3):

        all_vacancies = []
        page = 0

        params = {
            'text': query,
            'area': self._get_city_id(city) if city else 1,
            'page': page,
            'items_on_page': 20,
            'search_period': 30,
            'clusters': 'true',
            'enable_snippets': 'true',
            'no_magic': 'true',
            'order_by': 'publication_time',
            'search_field': 'name'
        }

        logger.info(f"Начинаем поиск: {query}, город: {city or 'Москва'}, ID города: {params['area']}")

        while page < max_pages:
            try:
                params['page'] = page

                url = f"{self.SEARCH_URL}?{urlencode(params, encoding='utf-8')}"

                logger.info(f"Запрос страницы {page + 1}: {url[:100]}...")

                time.sleep(random.uniform(2, 4))

                response = self.session.get(url, timeout=15)
                response.raise_for_status()

                response.encoding = 'utf-8'

                vacancies = self._parse_search_page(response.text)

                if not vacancies:
                    logger.info(f"На странице {page + 1} вакансии не найдены")
                    vacancies = self._parse_search_page_alternative(response.text)

                if vacancies:
                    logger.info(f"Найдено {len(vacancies)} вакансий на странице {page + 1}")
                    all_vacancies.extend(vacancies)
                    page += 1
                else:
                    logger.info("Больше вакансий не найдено, завершаем поиск")
                    break
                time.sleep(random.uniform(3, 5))

            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при запросе: {e}")
                break
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                break

        logger.info(f"Всего найдено вакансий: {len(all_vacancies)}")
        return all_vacancies

    def _parse_search_page(self, html):
        soup = BeautifulSoup(html, 'lxml')
        vacancies = []

        selectors = [
            'div.vacancy-serp-item',
            'div[data-qa="vacancy-serp__vacancy"]',
            'div.serp-item',
            'div.vacancy-card',
            'article.vacancy-card',
            'div.vacancy-preview-card'
        ]

        vacancy_items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                vacancy_items = items
                logger.info(f"Найдено вакансий по селектору '{selector}': {len(items)}")
                break

        if not vacancy_items:
            vacancy_items = soup.find_all('div', class_=re.compile(r'vacancy|serp-item|card'))
            logger.info(f"Найдено потенциальных вакансий: {len(vacancy_items)}")

        for item in vacancy_items:
            try:
                vacancy = self._parse_vacancy_item(item)
                if vacancy and vacancy.get('title') and vacancy.get('url'):
                    vacancies.append(vacancy)
            except Exception as e:
                logger.error(f"Ошибка при парсинге вакансии: {e}")
                continue

        return vacancies

    def _parse_search_page_alternative(self, html):
        soup = BeautifulSoup(html, 'lxml')
        vacancies = []

        links = soup.find_all('a', href=True)

        for link in links:
            try:
                href = link.get('href', '')
                if '/vacancy/' in href or 'vacancy' in href:
                    title = link.get_text().strip()
                    if title and len(title) > 3 and not any(
                            x in title.lower() for x in ['hh.ru', 'hh', 'вакансии', 'найти']):
                        parent = link.find_parent('div', class_=re.compile(r'item|card|row'))
                        if parent:
                            vacancy = self._parse_vacancy_item(parent)
                            if vacancy:
                                vacancies.append(vacancy)
            except Exception as e:
                continue

        return vacancies

    def _parse_vacancy_item(self, item):
        vacancy = {}

        title_selectors = [
            'a[data-qa="vacancy-serp__vacancy-title"]',
            'a.serp-item__title',
            'a.vacancy-card__title',
            'h3 a',
            'a[class*="title"]',
            'a[class*="Title"]'
        ]

        title_elem = None
        for selector in title_selectors:
            title_elem = item.select_one(selector)
            if title_elem:
                break

        if not title_elem:
            links = item.find_all('a')
            for link in links:
                text = link.get_text().strip()
                if text and len(text) > 3 and not any(x in text.lower() for x in ['hh.ru', 'откликнуться', 'показать']):
                    title_elem = link
                    break

        if title_elem:
            vacancy['title'] = title_elem.get_text().strip()
            vacancy['url'] = title_elem.get('href', '')
            if vacancy['url'] and not vacancy['url'].startswith('http'):
                vacancy['url'] = 'https://hh.ru' + vacancy['url']
        else:
            return None

        company_selectors = [
            'a[data-qa="vacancy-serp__vacancy-employer"]',
            'span[data-qa="vacancy-serp__vacancy-employer"]',
            'div.vacancy-serp-item__meta-info',
            'a[class*="company"]',
            'span[class*="company"]',
            'div[class*="company"]'
        ]

        company_elem = None
        for selector in company_selectors:
            company_elem = item.select_one(selector)
            if company_elem:
                break

        vacancy['company'] = company_elem.get_text().strip() if company_elem else 'Не указано'

        salary_selectors = [
            'span[data-qa="vacancy-serp__vacancy-compensation"]',
            'div.vacancy-serp-item__compensation',
            'span[class*="salary"]',
            'div[class*="salary"]'
        ]

        salary_elem = None
        for selector in salary_selectors:
            salary_elem = item.select_one(selector)
            if salary_elem:
                break

        vacancy['salary'] = salary_elem.get_text().strip() if salary_elem else 'Не указана'

        city_selectors = [
            'span[data-qa="vacancy-serp__vacancy-address"]',
            'span[class*="address"]',
            'div[class*="address"]',
            'span[class*="location"]',
            'div[class*="location"]'
        ]

        city_elem = None
        for selector in city_selectors:
            city_elem = item.select_one(selector)
            if city_elem:
                break

        if city_elem:
            city_text = city_elem.get_text().strip()
            vacancy['city'] = city_text.split(',')[0].strip()
        else:
            vacancy['city'] = 'Не указан'

        experience_selectors = [
            'div[data-qa="vacancy-serp__vacancy-work-experience"]',
            'span[class*="experience"]',
            'div[class*="experience"]'
        ]

        experience_elem = None
        for selector in experience_selectors:
            experience_elem = item.select_one(selector)
            if experience_elem:
                break

        vacancy['experience'] = experience_elem.get_text().strip() if experience_elem else 'Не указан'

        desc_selectors = [
            'div[data-qa="vacancy-serp__vacancy_snippet_requirement"]',
            'div[class*="snippet"]',
            'div[class*="description"]'
        ]

        desc_elem = None
        for selector in desc_selectors:
            desc_elem = item.select_one(selector)
            if desc_elem:
                break

        vacancy['description'] = desc_elem.get_text().strip() if desc_elem else ''

        vacancy['published_at'] = datetime.now()

        return vacancy

    def get_vacancy_details(self, url):
        try:
            time.sleep(random.uniform(1, 2))

            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'lxml')
            details = {}

            desc_elem = soup.find('div', {'data-qa': 'vacancy-description'})
            if desc_elem:
                details['description'] = desc_elem.get_text().strip()
            else:
                desc_elem = soup.find('div', class_=re.compile(r'description|vacancy-desc'))
                if desc_elem:
                    details['description'] = desc_elem.get_text().strip()

            requirements = []
            req_items = soup.find_all('li', {'data-qa': 'vacancy-requirement'})
            if req_items:
                requirements = [item.get_text().strip() for item in req_items]

            if not requirements:
                desc_text = details.get('description', '')
                if 'требован' in desc_text.lower():
                    lines = desc_text.split('\n')
                    for line in lines:
                        if 'требован' in line.lower():
                            requirements.append(line.strip())

            details['requirements'] = '\n'.join(requirements) if requirements else ''

            return details

        except Exception as e:
            logger.error(f"Ошибка при получении деталей вакансии {url}: {e}")
            return {}