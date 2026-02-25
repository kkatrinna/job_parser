from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class SearchQuery(db.Model):
    __tablename__ = 'search_queries'

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    results_count = db.Column(db.Integer, default=0)

    jobs = db.relationship('Job', backref='search', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SearchQuery {self.query}>'


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    salary = db.Column(db.String(100))
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    url = db.Column(db.String(500), unique=True)
    city = db.Column(db.String(100))
    experience = db.Column(db.String(100))
    employment_type = db.Column(db.String(50))
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    search_query_id = db.Column(db.Integer, db.ForeignKey('search_queries.id'))

    def __repr__(self):
        return f'<Job {self.title}>'

    def to_dict(self):
        return {
            'Название': self.title,
            'Компания': self.company,
            'Зарплата': self.salary,
            'Город': self.city,
            'Опыт работы': self.experience,
            'Тип занятости': self.employment_type,
            'Дата публикации': self.published_at.strftime('%d.%m.%Y') if self.published_at else '',
            'Ссылка': self.url,
            'Описание': self.description[:200] + '...' if self.description and len(
                self.description) > 200 else self.description
        }