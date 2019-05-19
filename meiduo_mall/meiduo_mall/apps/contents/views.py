from django.shortcuts import render
from django.views import View
from django.http import HttpResponseForbidden,JsonResponse
from django_redis import get_redis_connection

import re
import logging
import json

# from goods.models import GoodsChannel, GoodsCategory
# from goods.models import GoodsChannel,GoodsCategory
from .models import ContentCategory
from .utils import get_categories
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.sms.tasks import ccp_send_sms_code
from users.models import User
logger = logging.getLogger('django')
"""首页"""
class IndexView(View):
    def get(self, request):
        # 定义首页广告数据信息,用字典封装
        contents = {}
        # 获取所有的广告类型
        contents_qs = ContentCategory.objects.all()
        # 遍历得出每种广告类型
        for category in contents_qs:
            # 用广告类型别名字段key作为字典的键，该类型下所有的广告作为值,以sequence字段排序
            # 一方.多的一方小写_set()获得父类下的所有子类,status字段为是否展示
            contents[category.key] = category.content_set.filter(status=True).order_by('sequence')

        # 需要返回的数据
        context = {
            # 商品类型数据,categories为前端模板变量
            # 调用上面封装好的商品类型数据
            'categories':get_categories(),
            # 首页广告类型
            'contents': contents
        }

        return render(request, 'index.html', context)
    # def get(self, request):
    #
    #     contents = {}  # 用来装所有广告数据的字典
    #
    #     """
    #     {
    #         'index_lbt': lbt_qs,
    #         'index_kx': kx_qs
    #     }
    #     """
    #     contentCategory_qs = ContentCategory.objects.all()  # 获取所有广告类别数据
    #     for category in contentCategory_qs:
    #         contents[category.key] = category.content_set.filter(status=True).order_by('sequence')
    #
    #     context = {
    #         'categories': get_categories(),
    #         'contents': contents
    #
    #     }
    #     # print(context)
    #
    #     return render(request, 'index.html', context)
    #

"""密码找回"""
class PsswordbBack(View):
    def get(self,request):
        return render(request,'find_password.html')

"""第一步"""
class CheckDate(View):
    def get(self,request,username):
        image_code = request.GET.get('text')
        image_code_id = request.GET.get('image_code_id')
        if not re.match('[a-zA-Z0-9_-]{5,20}',username):
            return HttpResponseForbidden('无效用户名')
        redis_conn = get_redis_connection('verify_code')
        #取出图形验证码
        date = redis_conn.get('img_%s' % image_code_id)
        if date is None:
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'图形验证码失效'})
        if image_code.lower() != date.decode().lower():
            return HttpResponseForbidden('验证码错误')
        #获取当前用户填写的用户名，判断数据库中是否存在
        try:
            username = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'code':RETCODE.DBERR,'errmsg':'用户名不存在'})
        mobile = username.mobile
        password = username.password
        response = JsonResponse({'code':RETCODE.OK,'errmsg':'OK','mobile':mobile,'access_token':password})
        response.set_cookie('access_token',password,max_age=None)
        return response
"""第二步"""
class GetSmsCode(View):
    def get(self,request):
        password = request.COOKIES.get('access_token')
        try:
            user = User.objects.get(password=password)
            # pbkdf2_sha256$36000$pYlJBXo314NN$ijot9M902M4+CMxN7qh6W9NW542JTfH9krY+Io/NnjM=
        except User.DoesNotExist:
            return JsonResponse({'code':RETCODE.DBERR,'errmsg':'无效密码'})
        mobile = user.mobile
        redis_connet = get_redis_connection('verify_code')
        send_flag = redis_connet.get('send_flag_%s' % mobile)
        if send_flag:
            return JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})
        import random
        sms_code = '%06d' % random.randint(0, 999999)
        logger.info(sms_code)
        pl = redis_connet.pipeline()
        pl.setex('sms_%s' % mobile, 300, sms_code)
        pl.setex('send_flag_%s' % mobile, 60, 1)
        pl.execute()
        ccp_send_sms_code.delay(mobile, sms_code)
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '短信发送成功'})

"""第二步验证"""
class OrderSmsCode(View):
    def get(self,request,username):
        sms_code = request.GET.get('sms_code')
        user = User.objects.get(username=username)
        mobile = user.mobile
        access_token = user.password
        redis_connect = get_redis_connection('verify_code')
        sms_code_bytes = redis_connect.get('sms_%s' % mobile)
        if sms_code_bytes is None:
            return JsonResponse({'code':'400','errmsg':'手机验证码失效'})
        if int(sms_code) != int(sms_code_bytes):
            return JsonResponse({'code': '400', 'errmsg': '手机验证码错误'})
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK','user_id':user.id,'access_token':access_token})

"""第三步"""
class ToResetPassword(View):
    def post(self,request,user_id):
        json_dict = json.loads(request.body.decode())
        password = json_dict.get('password')
        password2 = json_dict.get('password2')
        access_token = json_dict.get('access_token')
        if not all([password,password2,access_token]):
            return HttpResponseForbidden('缺少必传参数')
        if not re.match('^[0-9A-Za-z]{8,20}',password):
            return HttpResponseForbidden('您输入的密码格式不正确')
        if password != password2:
            return HttpResponseForbidden('两次密码不一致')
        user = User.objects.get(id=user_id)
        if access_token == user.password:
            if user.check_password(password):
                return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '不能和近期密码相同'})
            else:
                user.set_password(password)
                user.save()
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

"""设置密码成功，返回登录页面"""
class BackLogin(View):
    def get(self,request):
        return render(request,'login.html')
