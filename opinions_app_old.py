import csv
from datetime import datetime
# Импортируется функция для выбора случайного значения:
from random import randrange

import click
from flask import Flask, abort, flash, redirect, render_template, url_for
from flask_migrate import Migrate
# Импортируем класс для работы с ORM:
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, URLField
from wtforms.validators import DataRequired, Length, Optional

app = Flask(__name__)
# Подключаем БД SQLite:
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
# Вместо MY SECRET KEY придумайте и впишите свой ключ:
app.config['SECRET_KEY'] = 'MY SECRET KEY'
# Создаём экземпляр SQLAlchemy и в качестве параметра
# передаём в него экземпляр приложения Flask:
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Opinion(db.Model):
    # ID — целое число, первичный ключ:
    id = db.Column(db.Integer, primary_key=True)
    # Название фильма — строка длиной 128 символов, не может быть пустым:
    title = db.Column(db.String(128), nullable=False)
    # Мнение о фильме — большая строка, не может быть пустым,
    # должно быть уникальным:
    text = db.Column(db.Text, unique=True, nullable=False)
    # Ссылка на сторонний источник — строка длиной 256 символов:
    source = db.Column(db.String(256))
    # Дата и время — текущее время,
    # по этому столбцу база данных будет проиндексирована:
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    added_by = db.Column(db.String(64))


# Класс формы Opinion.
class OpinionForm(FlaskForm):
    title = StringField(
        'Введите название фильма',
        validators=[DataRequired(message='Обязательное поле'),
                    Length(1, 128)]
    )
    text = TextAreaField(
        'Напишите мнение',
        validators=[DataRequired(message='Обязательное поле')]
    )
    source = URLField(
        'Добавьте ссылку на подробный обзор фильма',
        validators=[Length(1, 256), Optional()]
    )
    submit = SubmitField('Добавить')


@app.route('/')
def index_view():
    # Определяется количество мнений в базе данных:
    quantity = Opinion.query.count()
    # Если мнений нет...
    if not quantity:
        # ... то пользователь увидит ошибку 500:
        abort(500)
    # Иначе выбирается случайное число в диапазоне от 0 до quantity,
    offset_value = randrange(quantity)
    # и определяется случайный объект - берём первую запись, из получившегося:
    opinion = Opinion.query.offset(offset_value).first()
    # Передаём в шаблон объект opinion:
    return render_template('opinion.html', opinion=opinion)


@app.route('/add', methods=['GET', 'POST'])
def add_opinion_view():
    # Создаётся новый экземпляр формы:
    form = OpinionForm()
    # Если ошибок не возникло...
    if form.validate_on_submit():
        # ...то нужно создать новый экземпляр класса Opinion:
        text = form.text.data
        # Если в БД уже есть мнение с текстом, который ввёл пользователь...
        if Opinion.query.filter_by(text=text).first() is not None:
            # ...вызвать функцию flash и передать соответствующее сообщение:
            flash('Такое мнение уже было оставлено ранее!')
            # Вернуть пользователя на страницу «Добавить новое мнение»:
            return render_template('add_opinion.html', form=form)
        opinion = Opinion(
            # И передать в него данные, полученные из формы:
            title=form.title.data,
            text=form.text.data,
            source=form.source.data
        )
        # Затем добавить его в сессию работы с базой данных:
        db.session.add(opinion)
        # И зафиксировать изменения:
        db.session.commit()
        # Затем переадресовать пользователя на страницу добавленного мнения:
        return redirect(url_for('opinion_view', id=opinion.id))
    # Если валидация не пройдена — просто отрисовать страницу с формой.
    # Объект формы передаётся в шаблон add_opinion.html:
    return render_template('add_opinion.html', form=form)


# Тут указывается конвертер пути для id:
@app.route('/opinions/<int:id>')
# Параметром указывается имя переменной:
def opinion_view(id):
    # Теперь можно запросить нужный объект по id,
    # а метод get() прописываем как get_or_404(), чтобы сайт не упал с ошибкой
    opinion = Opinion.query.get_or_404(id)
    # ...и передаём его в шаблон (шаблон тот же, что и для главной страницы):
    return render_template('opinion.html', opinion=opinion)


@app.errorhandler(500)
def internal_error(error):
    # Ошибка 500 возникает в нештатных ситуациях на сервере.
    # Например, провалилась валидация данных.
    # В таких случаях можно откатить изменения, не зафиксированные в БД,
    # чтобы в базу не записалось ничего лишнего.
    db.session.rollback()
    # Пользователю вернётся страница, сгенерированная на основе шаблона 500.html.
    # Этого шаблона пока нет, но сейчас мы его тоже создадим.
    # Пользователь получит и код HTTP-ответа 500.
    return render_template('500.html'), 500


@app.errorhandler(404)
def page_not_found(error):
    # При ошибке 404 в качестве ответа вернётся страница, созданная
    # на основе шаблона 404.html, и код HTTP-ответа 404:
    return render_template('404.html'), 404


@app.cli.command('load_opinions')
def load_opinions_command():
    """Функция загрузки мнений в базу данных."""
    # Открываем файл:
    with open('opinions.csv', encoding='utf-8') as f:
        # Создаём итерируемый объект, который отображает каждую строку
        # в качестве словаря с ключами из шапки файла:
        reader = csv.DictReader(f)
        # Для подсчёта строк добавляем счётчик:
        counter = 0
        for row in reader:
            # Распакованный словарь используем
            # для создания экземпляра модели Opinion:
            opinion = Opinion(**row)
            # Добавляем объект в сессию и коммитим:
            db.session.add(opinion)
            db.session.commit()
            counter += 1
    click.echo(f'Загружено мнений: {counter}')


if __name__ == '__main__':
    app.run()
