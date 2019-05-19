from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse,HttpResponseForbidden
from meiduo_mall.utils.response_code import RETCODE
from django.utils import timezone
from django_redis import get_redis_connection

import json
from decimal import Decimal

from users.models import Address
from carts.models import OrderInfo,OrderGoods
from goods.models import SKU
"""提交订单"""
class OrderCommitView(LoginRequiredMixin, View):
    def post(self,request):
        # 获取请求体数据
        json_dict = json.loads(request.body.decode())
        # 获取用户勾选的地址id
        address_id = json_dict.get('address_id')
        # 获取用户付款方式
        pay_method = json_dict.get('pay_method')
        # 校验数据
        try:
            address = Address.objects.get(id=address_id, is_deleted=False)
        except Address.DoesNotExist:
            return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '无效地址'})
        # 判断支付方式是否有效,参考数据在carts模型的OrderInfo里
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '支付方式有误'})
        # 获取当前用户
        user = request.user
        # 获取当前时间
        stri_new_time = timezone.localtime()
        new_time = stri_new_time.strftime('%Y%m%d%H%M%S')  # 将当前时间转成字符串
        # 生成一个订单编号order_id，格式：时间 + (‘%09d’ % user.id)
        order_id = new_time + ('%09d' % user.id)

        """使用事务保存订单数据"""
        """创建事务"""
        from django.db import transaction
        with transaction.atomic():
            """创建保存点，没有提交事务前回滚到指定地方"""
        save_id = transaction.savepoint()

        try:
            # 创建订单数据
            order_info = OrderInfo.objects.create(
                order_id=order_id,  # 订单编号
                user=user,  # 下单用户
                address=address,  # 收货地址
                total_count=0,  # 商品数量，先设置为0
                total_amount=Decimal('0.00'),  # 商品总价，先设置为0
                freight=Decimal('10.00'),  # 运费
                pay_method=pay_method,  # 支付方式
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else
                OrderInfo.ORDER_STATUS_ENUM['UNSEND'],
            )

            # 建立redis数据库链接
            redis_connect = get_redis_connection('carts')
            # 获取hash数据，只为获得count
            sku_cont_dict = redis_connect.hgetall('carts_%s' % user.id)
            # 只获取勾选中的商品sku_id
            selected_sku_id = redis_connect.smembers('selected_%s' % user.id)
            # 建立一个字典重新组成以sku_id为键,count为值
            new_carts_dict = {}
            # 遍历被勾选中的sku_id
            for sku_id in selected_sku_id:
                # 组成字典
                new_carts_dict[int(sku_id)] = int(sku_cont_dict[sku_id])
            # 获取字典中的sku_id
            skus_id = new_carts_dict.keys()

            # 遍历获取每个sku_id
            for sku_id in skus_id:
                """用户下单失败，无限循环，直到库存不足"""
                while True:
                    sku = SKU.objects.get(id=sku_id)
                    # 获取当前商品数量
                    count = new_carts_dict[sku.id]

                    # 判断库存是否充足
                    if count > sku.stock:
                        """事务回滚到指定起始点"""
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '库存不足'})

                        # sku库存字段减少，销量字段增加
                        # sku.stock -= count
                        # sku.sales += count
                        # 保存
                        # sku.save()

                    # sku库存字段减少，销量字段增加
                    new_stock = sku.stock - count
                    new_sales = sku.sales + count

                    """
                    使用乐观锁更新库存和销量，假如有两个用户同时购买5件相同的商品,库存为8,
                    使用乐观锁更新库存，只有一个用户会下单成功，另一个用户会被阻塞直到上一个用户订单完成提交事物
                    轮到操作该用户的订单时，由于上一个用户完成了下单，库存发生了变化,stock=sku.stock条件不在成立
                    更新失败时返回更新的数据条数0,
                    """
                    result = SKU.objects.filter(id=sku_id, stock=sku.stock).update(stock=new_stock, sales=new_sales)
                    """返回的是修改成功的条数"""
                    if result == 0:
                        """
                        如果同时下单,肯定有一个更改失败，不是库存不足问题，而是更新不了（条件不成立）数据问题
                        跳出本次循环，让该用户重新执行下单，除非库存不足返回响应
                        默认无限机会，根据需求修改下单几次会失败
                        """
                        continue
                        # 获取sku对应的spu
                    spu = sku.spu
                    # spu销量字段增加
                    spu.sales += count
                    spu.save()

                    # 创建商品信息表
                    OrderGoods.objects.create(
                        order=order_info,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )
                    # 订单数据表对应的数量，总价增加
                    order_info.total_count += count
                    order_info.total_amount += (sku.price * count)

                    """一个订单完成，结束死循环"""
                    break

        except Exception:
            """回滚事务，返回响应"""
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'code': 'OK', 'errmsg': '下单失败'})
        else:
            """当下单成功，数据库操作完成，提交事务"""
            transaction.savepoint_commit(save_id)

        # 订单总价=加上运费
        order_info.total_amount = order_info.total_amount + order_info.freight
        # 保存
        order_info.save()

        # 清除redis中以提交订到的商品
        pl = redis_connect.pipeline()
        pl.hdel('carts_%s' % user.id, *skus_id)
        pl.delete('selected_%s' % user.id, *skus_id)
        pl.execute()

        # 返回响应
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '提交成功', 'order_id': order_id})

"""展示提交订单成功界面"""
class OrderSuccessView(LoginRequiredMixin,View):
    def get(self, request):

        # 接收查询参数
        query_dict = request.GET
        order_id = query_dict.get('order_id')
        payment_amount = query_dict.get('payment_amount')
        pay_method = query_dict.get('pay_method')

        # 校验
        try:
            OrderInfo.objects.get(order_id=order_id, pay_method=pay_method, total_amount=payment_amount)
        except OrderInfo.DoesNotExist:
            return HttpResponseForbidden('订单有误')



        # 包装要传给模板的数据
        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }

        return render(request, 'order_success.html', context)

"""待评价"""
class OrderCommentView(LoginRequiredMixin, View):
    """待评价页面"""
    def get(self,request):
        #获取订单编号
        order_id = request.GET.get('order_id')
        #校验
        try:
            OrderInfo.objects.get(order_id=order_id)
        except OrderInfo.DoesNotExist:
            return HttpResponseForbidden('参数有误')
        #获取订单的所有未评价的商品
        order_goods = OrderGoods.objects.filter(order_id=order_id,is_commented=False)
        #创建列表,包装每种商品的信息
        goods_list = []
        #获取订单下的每种商品
        for goods in order_goods:
            goods_list.append({
                'order_id':goods.order_id,
                'sku_id':goods.sku_id,
                'name':goods.sku.name,
                'price':str(goods.sku.price),
                'default_image_url':goods.sku.default_image.url,
                'comment':goods.comment,
                'score':goods.score,
                'is_anonymous':str(goods.is_anonymous)
            })
        #渲染模板
        context = {
            'uncomment_goods_list':goods_list,
        }

        return render(request,'goods_judge.html',context)

    """提交评价"""
    def post(self,request):
        #获取请求体参数
        json_dict = json.loads(request.body.decode())
        #获取每个数据
        order_id = json_dict.get('order_id')
        sku_id = json_dict.get('sku_id')
        comment = json_dict.get('comment')
        score = json_dict.get('score')
        is_anonymous = json_dict.get('is_anonymous')

        #校验参数
        if not all([order_id,sku_id,score]):
            return HttpResponseForbidden('参数有误')
        try:
            OrderInfo.objects.get(order_id=order_id,user=request.user,status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
            sku = SKU.objects.get(id=sku_id)
        except OrderInfo.DoesNotExist:
            return HttpResponseForbidden('订单错误')
        if is_anonymous:
            if not isinstance(is_anonymous,bool):
                return HttpResponseForbidden('非指定参数')

        #保存订单商品评价数据
        OrderGoods.objects.filter(order_id=order_id,sku_id=sku_id,is_commented=False).update(
            comment=comment,
            score=score,
            is_anonymous=is_anonymous,
            is_commented=True
        )
        #商品评价+1
        sku.comments+=1
        sku.save()
        #spu商品类型评价+1
        sku.spu.comments+=1
        sku.spu.save()

        #如果该订单下的所有商品都评价了,修改订单状态为完成
        if OrderGoods.objects.filter(order_id=order_id,is_commented=False).count() == 0:
            OrderInfo.objects.filter(order_id=order_id).update(status=OrderInfo.ORDER_STATUS_ENUM['FINISHED'])

        return JsonResponse({'code':RETCODE.OK,'errmsg':'评价成功'})