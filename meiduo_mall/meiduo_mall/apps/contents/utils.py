from goods.models import GoodsChannel

# def get_categories():
#     #返回商品数据
#     categories = {}#包装所有商品类别数据
#     #获取所有1级类别分组数据
#     goods_channels_qs = GoodsChannel.objects.order_by('group_id','sequence')
#
#     #遍历数据
#     for channel in goods_channels_qs:
#         #获取组商品所在组的id
#         group_id = channel.group_id
#         #判断当前组id是否存在字典中
#         if group_id not in categories:
#             #不存在时,包装一个组的准备数据
#             categories[group_id] = {'channels':[],'cat_subs':[]}
#         #获取1级数据对象
#         cat1 = channel.category
#         #顶级数据对象没有url属性,将频道中的url绑定到顶级数据
#         cat1.url = channel.url
#         #向字典添加1级数据
#         categories[group_id]['channels'].append(cat1)
#
#         #获取当前组下的所有二级(子级)数据
#         cat2_qs = cat1.subs.all()
#         for cat2 in cat2_qs:
#             #获取第三级数据
#             cat3 = cat2.subs.all()
#             #把cat2下的所有3级绑定给cat2的cat_subs属性
#             cat2.cat_subs = cat3
#             #向字典添加2级数据
#             categories[group_id]['cat_subs'].append(cat2)
#
#     return categories


def get_categories():
    """返回商品类别数据"""

    categories = {}  # 用来包装所有商品类别数据
    # 获取所有一级类别分组数据,该表已经分好组,一行就是一组数据,sequence字段代表的是每一行的排序
    goods_channels_qs = GoodsChannel.objects.order_by('group_id', 'sequence')

    #遍历获得的是每一个顶级数据对象
    for channel in goods_channels_qs:

        group_id = channel.group_id  # 获取当前对象所在组id

        # 判断当前数据对象组id在字典中是否存在
        if group_id not in categories:
            # 不存在,包装一个当前组的准备数据,接下来channels的值封装着顶级数据，cat_subs封装的是顶级数据的子级,他是自关联对象,
            #通过顶级数据对象.subs.all()获得所有2级数据,2级数据对象.subs.all()获得所有3级数据对象
            categories[group_id] = {'channels': [], 'cat_subs': []}

        cat1 = channel.category  # 获取一级类别数据对象
        cat1.url = channel.url  # 将频道中的url绑定给一级类型数据对象
        categories[group_id]['channels'].append(cat1)#往列表添加1级数据对象

        cat2_qs = cat1.subs.all()  # 获取1级(父级)数据对象下的所有二级(子级)数据,它是自关联的表
        for cat2 in cat2_qs:  # 遍历得到每个2级数据对象
            cat3_qs = cat2.subs.all()  # 获取当前二级下面的所有三级 得到三级查询集
            cat2.cat_subs = cat3_qs  # 把二级下面的所有三级绑定给cat2对象的cat_subs属性
            categories[group_id]['cat_subs'].append(cat2)#往列表添加2级数据对象，3级数据已经绑定在2级数据对象,通过2级数据对象.cat_subs获得

    return categories