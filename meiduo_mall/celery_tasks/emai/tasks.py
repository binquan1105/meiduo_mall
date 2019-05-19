
from celery_tasks.main import celery_add
from django.core.mail import send_mail

from django.conf import settings

@celery_add.task(bind = True,name='send_email_celery')
def send_email_celery(self,to_email,verify_url):
    subject = "美多商城邮箱验证"  # 邮箱主题
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用美多商城。</p>' \
                   '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s</a></p>' % (to_email, verify_url, verify_url)
    try:
        send_mail(subject, "", settings.EMAIL_FROM, ['itheima_cast@163.com'], html_message=html_message)

    except Exception as e:
        raise self.retry(exc=e,max_retries=3)

