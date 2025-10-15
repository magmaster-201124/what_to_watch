from datetime import datetime, UTC
# Если у вас установлен Python до версии 3.11, используйте другой импорт:
# from datetime import datetime, timezone
# А также поменяйте в коде UTC на timezone.utc

from . import db


class Opinion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    text = db.Column(db.Text, unique=True, nullable=False)
    source = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    added_by = db.Column(db.String(64))

    def to_dict(self):
        return dict(
            id=self.id,
            title=self.title,
            text=self.text,
            source=self.source,
            timestamp=self.timestamp,
            added_by=self.added_by
        )

    # Метод-десериализатор.
    # На вход метод принимает словарь data, полученный из JSON в запросе.
    def from_dict(self, data):
        # Для каждого поля модели, которое можно заполнить...
        for field in ['title', 'text', 'source', 'added_by']:
            # .выполняется проверка — есть ли ключ с таким же именем в словаре:
            if field in data:
                # Если есть, добавляем значение из словаря
                # в соответствующее поле объекта модели:
                setattr(self, field, data[field])
