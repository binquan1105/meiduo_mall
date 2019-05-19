import pickle,base64
from django_redis import get_redis_connection

"""合并购物车"""
"""
3.1 Redis数据库中的购物车数据保留。
3.2 如果cookie中的购物车数据在Redis数据库中已存在，将cookie购物车数据覆盖Redis购物车数据。
3.3 如果cookie中的购物车数据在Redis数据库中不存在，将cookie购物车数据新增到Redis。
3.4 最终购物车的勾选状态以cookie购物车勾选状态为准。
"""

def merge_cart_cookie_to_redis(request,user,response):
    """
    request:请求对象，获取cookie时需要用到的参数
    user:注意，当用户登录时第一次发送请求只是将user用户存到session中，并不能通过request.user获得登录用户，需要借用user = authenticate(username=username,password=password)判断是否登录时的user作为参数传进来
    response:响应体数据,响应体作为对象，经过调用此方法，响应体已发送改变，可以不用返回response

    """
    # 获取cookie数据
    carts = request.COOKIES.get('carts')
    # 如果有数据，解码转成字典
    if carts:
        carts_dict = pickle.loads(base64.b64decode(carts.encode()))
    # 如果没有，退出
    else:
        return
    # 建立redis链接
    redis_connect = get_redis_connection('carts')
    # 建立管道
    pl = redis_connect.pipeline()
    # 遍历字典，获取所有sku_id,和值
    for sku_id, sku_dict in carts_dict.items():
        # 将count,sku_id以hash类型存储到redis中
        pl.hset('carts_%s' % user.id, sku_id, sku_dict['count'])
        # 如果是勾选的商品,将sku_id以set类型存储到redis中
        if sku_dict['selected']:
            pl.sadd('selected_%s' % user.id, sku_id)
        # 如果每勾选,删除set类型中对应的数据
        else:
            pl.srem('selected_%s' % user.id, sku_id)
    # 执行管道
    pl.execute()

    # 清除cookie中的carts购物车数据
    response.delete_cookie('carts')

    """响应体数据,响应体作为对象，经过调用此方法，响应体已发生改变，可以不用返回response"""

"""方式二"""
    # """
    # 登录后合并cookie购物车数据到Redis
    # :param request: 本次请求对象，获取cookie中的数据
    # :param user: 登录用户信息，获取user_id
    # :param response: 本次响应对象，清除cookie中的数据
    # :return:
    # """
    # #获取cookie中的购物车信息
    # carts = request.COOKIES.get('carts')
    # #如果有数据转成字典
    # if carts:
    #     carts_dict =  pickle.loads(base64.b64decode(carts.encode()))
    # #没有数据返回
    # else:
    #     return
    # #创建一个列表，以sku_id作为建,count作为值,为了以hash类型存到redis
    # carts_sku_count = {}
    # #cookie中保存的selected可能为True，可能为False，分两种情况,创建两个表
    # new_selected_True = []
    # new_selected_False = []
    # #遍历获得每个sku_id
    # for sku_id in carts_dict.keys():
    #     #组成一个新的字典
    #     carts_sku_count[sku_id] = carts_dict[sku_id]['count']
    #     #获取selected的值
    #     selected = carts_dict[sku_id]['selected']
    #     # 如果为True
    #     if selected:
    #         #将此商品id追加到True列表中
    #         new_selected_True.append(sku_id)
    #     #反之追加到False列表中
    #     else:
    #         new_selected_False.append(sku_id)
    #
    # #建redis数据库链接
    # redis_connect = get_redis_connection('carts')
    # pl = redis_connect.pipeline()
    # #以hash类型存到redis数据库
    # pl.hmset('carts_%s' % user.id,carts_sku_count)
    # #只保存勾选状态的sku_id
    # if new_selected_True:
    #     pl.sadd('selected_%s' % user.id,*new_selected_True)#解包
    # #没勾选的删除
    # if new_selected_False:
    #     pl.srem('selected_%s' % user.id,*new_selected_False)#解包
    # #执行
    # pl.execute()
    # #清除cookie
    # response.delete_cookie('carts')
    # #response对象已经修改,不需要返回
    # return response

