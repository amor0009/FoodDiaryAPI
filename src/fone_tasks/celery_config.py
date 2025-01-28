from celery import Celery
from celery.schedules import crontab
from task import start_rabbitmq_consumer

celery = Celery(
    __name__,
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Функция для старта consumer при запуске Celery worker
@celery.on_after_configure.connect
def setup_rabbitmq_consumer(sender, **kwargs):
    sender.add_periodic_task(10.0, start_rabbitmq_consumer.s(), name="Start RabbitMQ Consumer")

celery.conf.beat_schedule = {
    'delete-old-user-weights-every-day': {
        'task': 'tasks.delete_old_user_weights',  # имя задачи из tasks.py
        'schedule': crontab(hour=0, minute=0),    # запуск каждый день в полночь
    },
    'delete-old-meal-products-every-day': {
        'task': 'tasks.delete_old_meal_products',
        'schedule': crontab(hour=0, minute=0),    # запуск каждый день в полночь
    },
}
