from django.views import View
from django.http import HttpResponse,JsonResponse
from django_redis import get_redis_connection
from meiduo_mall.libs.response_code import RETCODE
import logging
from celery_tasks.sms.tasks import ccp_send_sms_code
from . import contans
logger = logging.getLogger('django')
# 利用SDK 生成图形验证码 (唯一标识字符串, 图形验证内容字符串, 二进制图片数据)
#这个模块包是自己复制过来的
from meiduo_mall.libs.captcha.captcha import captcha

class ImageCodeView(View):
    """生成图形验证码"""

    def get(cls, request, uuid):
        """
        :param uuid: 唯一标识,用来区分当前的图形验证码属于那个用户
        :return: image
        """

        # 利用SDK 生成图形验证码 (唯一标识字符串, 图形验证内容字符串, 二进制图片数据)

        name, text, image = captcha.generate_captcha()

        # 创建redis连接对象
        redis_conn = get_redis_connection('verify_code')
        # 将图形验证码字符串存入到redis
        redis_conn.setex('img_%s' % uuid, contans.SETEX_EXPIRE, text)
        # 把生成好的图片响应给前端

        # print(redis_conn.get('img_%s' % uuid))
        return HttpResponse(image, content_type='image/png')

class SMSCodeView(View):
    #将手机号码传入
    def get(self, reqeust, mobile):
        #避免60秒重复刷新，判断数据库是否有验证码，有就返回错误状态码，前端接受状态码渲染页面
        #建立连接
        redis_connet = get_redis_connection('verify_code')
        #获取短信验证码标识,60秒过期
        send_flag = redis_connet.get('send_flag_%s' % mobile)
        if send_flag:
            return JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})
        #获取路径参数,图形验证码,UUID
        image_code_client = reqeust.GET.get('image_code')
        uuid = reqeust.GET.get('uuid')
        #判断是否传入数据
        if not all([image_code_client,uuid]):
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'缺少必传参数'})

        # #与redis建立连接,获取redis连接对象
        # redis_connet = get_redis_connection('verify_code')
        #提取验证码
        image_code_server = redis_connet.get('img_%s' % uuid)
        #判断图形验证码是否存在或过期
        if image_code_server is None:
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'图形验证码失效'})
        #删除图形验证码
        try:
            redis_connet.delete('img_%s' % uuid)

        except Exception as e:
            logger.error(e)
        #对比图形验证码,图形验证码为btype类型,转成字符串
        if image_code_client.lower() != image_code_server.decode().lower():
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'图形验证码失败'})


        #生成短信验证码:生成随机六位数
        import random
        #不够6位数用0补充
        sms_code = '%06d' % random.randint(0,999999)
        #打印日记信息，是否接收到短信验证码
        logger.info(sms_code)
        print(sms_code)

        #访问redis操作用管道方法实现，为了提高效率
        #创建管道管理
        pl = redis_connet.pipeline()
        #将访问redis操作添加到队列
        pl.setex('sms_%s' % mobile, contans.SETEX_EXPIRE, sms_code)
        pl.setex('send_flag_%s' % mobile, 60, 1)
        #注意：完成上面操作一定要执行
        pl.execute()

        # 把短信验证码存到redis数据库中,将魔法数字存到一个文件中
        # redis_connet.setex('sms_%s' % mobile, contans.SETEX_EXPIRE, sms_code)
        # 重新写入一个redis标记短信验证码,为了避免刷新页面发送短信,开头设置判断条件
        # redis_connet.setex('send_flag_%s' % mobile, 60, 1)


        #发送验证码,格式：导入第三方包，用实例类的send_template_sms方法发送
        #参数：mobile:要发送的手机号码、第二个参数为列表:[短信验证码,多长时间过期(单位是分钟,数据库设置多少就整除60)]
        #第三个参数为使用的短信模板，设置云通讯的sms文件配置,修改三个参数
        #_accountSid、_accountToken、_appId

        #执行发送短信是要时间的，为了避免长时间没有返回信息，使用celery架构
        # CCP().send_template_sms(mobile,[sms_code,contans.SETEX_EXPIRE // 60],contans.SEND_CODE_NUBER)

        #调用celery,注意：使用delay()方法将任务添加到经纪人/管理器,把手机，验证码作为参数传过去,任务接收参数
        ccp_send_sms_code.delay(mobile,sms_code)
        #在终端开启celery构架celery -A celery_tasks.main worker -l info

        #发送成功，返回响应,前端要的是json数据
        return JsonResponse({'code':RETCODE.OK,'errmsg':'短信发送成功'})

