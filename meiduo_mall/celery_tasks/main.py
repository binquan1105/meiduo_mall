#这是启动文件
from celery import Celery
import os
#告诉celery使用本项目的配置文件
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")
#指定经纪人
celery_add = Celery('meiduo')

#加载config配置

celery_add.config_from_object('celery_tasks.config')#加载路径

#自动注册任务
celery_add.autodiscover_tasks(['celery_tasks.sms','celery_tasks.email'])