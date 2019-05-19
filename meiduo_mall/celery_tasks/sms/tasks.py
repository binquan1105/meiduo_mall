#文件名固定
#导入执行文件指定经纪人
from celery_tasks.main import celery_add
from celery_tasks.sms.yuntongxun.sms import CCP
import logging
logger = logging.getLogger('django')
#使用经纪人装饰任务
#bind:保证task对象作为第一个参数传入
#name:起任务别名
#retry_backoff:异常自动重试时间间隔
#max_retries:一场自动重试最多此数
# @celery_add.task(bind=True,name='tasks_sms_code',retry_backoff=3)
@celery_add.task(bind=True,name='tasks_sms_code')
def ccp_send_sms_code(self,mobile,sms_code):
    try:
        print('mobile:',mobile)
        print('sms_code:',sms_code)
        #发送成功返回0，发送失败返回-1
        sen_data = CCP().send_template_sms(mobile,[sms_code,5],1)
    except Exception as e:
        logger.error(e)
        #有异常最多重试此数,重试三次
        raise self.retry(exc=e,max_retries=3)
    if sen_data != 0:
        #有异常自动重试次数
        raise self.retry(exc=Exception('发送短信失败'),max_retries=3)

    return sen_data