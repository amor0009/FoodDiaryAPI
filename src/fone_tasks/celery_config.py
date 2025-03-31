from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

# Инициализация Celery
celery = Celery(
    'tasks',
    broker='amqp://dev:dev@rabbitmq:5672//fooddiary',  # Используем новый vhost
    backend='rpc://',
    include=['src.fone_tasks']  # Путь к модулю с задачами
)

# Настройки Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    task_default_queue='default',
    task_queues=[
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('registration_queue', Exchange('registration'), routing_key='registration'),
        Queue('cleanup_queue', Exchange('cleanup'), routing_key='cleanup'),
    ],
    task_routes={
        'start_rabbitmq_consumer': {'queue': 'registration_queue'},
        'delete_old_user_weights': {'queue': 'cleanup_queue'},
        'delete_old_meal_products': {'queue': 'cleanup_queue'},
        'add_daily_weight_records': {'queue': 'cleanup_queue'},
    },
    beat_schedule={
        'delete-old-weights': {
            'task': 'delete_old_user_weights',
            'schedule': crontab(hour=0, minute=0),  # Запускать ежедневно
        },
        'delete-old-meals': {
            'task': 'delete_old_meal_products',
            'schedule': crontab(hour=0, minute=0),
        },
        'add-daily-weights': {
            'task': 'add_daily_weight_records',
            'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
        },
    }
)
