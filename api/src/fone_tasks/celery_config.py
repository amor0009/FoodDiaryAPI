from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

celery_app = Celery(
    'tasks',
    broker='amqp://dev:dev@localhost:5672/fooddiary',
    backend='rpc://',
    include=['api.src.fone_tasks.task']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    task_default_queue='default',
    task_queues=[
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('registration_queue', Exchange('registration'), routing_key='registration'),
        Queue('email_queue', Exchange('email'), routing_key='email'),
        Queue('cleanup_queue', Exchange('cleanup'), routing_key='cleanup'),
    ],
    task_routes={
        'start_rabbitmq_consumer': {'queue': 'registration_queue'},
        'send_code': {'queue': 'email_queue'},
        'delete_old_user_weights': {'queue': 'cleanup_queue'},
        'delete_old_meal_products': {'queue': 'cleanup_queue'},
        'add_daily_weight_records': {'queue': 'cleanup_queue'},
    },
    beat_schedule={
        'delete-old-weights': {
            'task': 'delete_old_user_weights',
            'schedule': crontab(hour=0, minute=0),
        },
        'delete-old-meals': {
            'task': 'delete_old_meal_products',
            'schedule': crontab(hour=0, minute=0),
        },
        'add-daily-weights': {
            'task': 'add_daily_weight_records',
            'schedule': crontab(hour=3, minute=0),
        },
    }
)