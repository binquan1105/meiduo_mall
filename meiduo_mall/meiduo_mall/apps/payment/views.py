from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from alipay import AliPay#支付宝SDK对接，需要安装pip3 install python-sdk --upgrade
from django.http import  HttpResponseForbidden,JsonResponse

from carts.models import OrderInfo
from django.conf import settings
from meiduo_mall.utils.response_code import RETCODE
from .models import Payment
import os
"""生成支付宝登录链接"""
class PaymentView(LoginRequiredMixin, View):
    def get(self,request,order_id):
        #获取用户
        user = request.user
        try:
            #获取当前订单
            order = OrderInfo.objects.get(order_id=order_id,user=user,status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return HttpResponseForbidden('订单有误')

        #创建支付宝支付对象
        alipay = AliPay(
            #应用appid
            appid=settings.ALIPAY_APPID,
            #默认回调，使用None
            app_notify_url=None,
            #应用私钥 路径指定，当前的绝对路径为apps
            #os.path.dirname(os.path.abspath(__file__)) 当前路径的上级路径，也就是keys
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),            #支付宝公钥，指定路径
            #支付宝公钥
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/alipay_public_key.pem"),
            #加密方式:RSA/RSA2
            sign_type="RSA2",
            #是否为沙箱环境,默认为False
            debug=settings.ALIPAY_DEBUG,
        )

        #生成登录支付链接
        order_string = alipay.api_alipay_trade_page_pay(
            #支付订单
            out_trade_no=order_id,
            #支付总价
            total_amount=str(order.total_amount),
            #支付标题
            subject="美多商城%s" % order_id,
            #支付成功回调地址
            return_url=settings.ALIPAY_RETURN_URL,
        )
        # 响应登录支付宝连接
        # 真实环境电脑网站支付网关：https://openapi.alipay.com/gateway.do? + order_string
        # 沙箱环境电脑网站支付网关：https://openapi.alipaydev.com/gateway.do? + order_string
        alipay_url = settings.ALIPAY_URL + "?" + order_string
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'alipay_url': alipay_url})

"""支付成功的回调处理"""
class PaymentStatusView(View):
    def get(self,request):
        #获取请求参数，类型是query_dict类型
        query_dict = request.GET
        #将query_dict类型转成字典
        date = query_dict.dict()
        #传过来的字符串多了签名属性，将它剔除
        signature = date.pop('sign')

        #创建支付宝支付对象
        alipay = AliPay(
            #应用APPID
            appid=settings.ALIPAY_APPID,
            #回调URL,使用None
            app_notify_url=None,
            #私钥地址
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),            #支付宝公钥，指定路径
            #支付宝公钥地址
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/alipay_public_key.pem"),
            #签名方式RSA/RSA2
            sign_type="RSA2",
            #是否为沙箱环境
            debug=settings.ALIPAY_DEBUG,
        )

        #判断重定向是否为alipay重定向过来的verify(剔除签名后的字符串参数，签名)
        succes = alipay.verify(date,signature)
        if succes:
            #获取支付成功的订单编号
            order_id = date.get('out_trade_no')
            #获取支付成功支付宝流水编号
            trade_id = date.get('trade_no')

            #先获取当前的交易数据，保证唯一
            try:
                Payment.objects.get(order_id=order_id,trade_id=trade_id)
            except Payment.DoesNotExist:
                #保存交易数据
                Payment.objects.create(
                    order_id = order_id,
                    trade_id = trade_id,
                )
                #修改订单状态
                OrderInfo.objects.filter(order_id=order_id,status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(
                    order_id=order_id,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'],
                )

            #渲染页面
            context = {
                'trade_id':trade_id,
            }
            return render(request,'pay_success.html',context)
        else:
            return HttpResponseForbidden('请求出错')