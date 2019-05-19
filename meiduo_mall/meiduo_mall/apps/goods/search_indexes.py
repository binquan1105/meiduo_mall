#haystack建立数据索引文件
#当前py文件名必须是:search_indexes.py
from haystack import indexes

from .models import SKU#本项目对sku信息进行全文索引

#定义一个类
class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    """SKU索引数据模型类"""
    #固定写法
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        """返回建立索引的模型类"""
        #可修改
        return SKU#需要建立数据索引的模型类对象

    def index_queryset(self, using=None):
        """返回要建立索引的数据查询集"""
        #可修改
        return self.get_model().objects.filter(is_launched=True)