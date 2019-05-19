from django.db import models

class Area(models.Model):
    """省市区"""
    name = models.CharField(max_length=20, verbose_name='名称')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='subs', null=True, blank=True, verbose_name='上级行政区划')

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '省市区'
        verbose_name_plural = '省市区'

    def __str__(self):
        return self.name

 #参数说明
 #自关联字段的外键指向自身,所以用models.Foreignkey('self')
 #使用releted_name指明父级查询子级数据的语法，如省查市
 	#默认 Area模型类对象.area_set语法
 #使用related_name = 'subs'
 	#现在用的是Area模型类对象.subs语法
# Create your models here.
