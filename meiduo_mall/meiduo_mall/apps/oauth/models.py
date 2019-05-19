from django.db import models

from meiduo_mall.utils.models import QQuserDate


class OAuthQQUser(QQuserDate):
    """QQ登录用户数据"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name='用户')
    openid = models.CharField(max_length=64, verbose_name='openid', db_index=True)

    class Meta:
        db_table = 'tb_oauth_qq'
        verbose_name = 'QQ登录用户数据'
        verbose_name_plural = verbose_name


"""weibo登录用户模型类"""
class OAuthSinaUser(QQuserDate):
    """
    Sina登录用户数据
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name='用户')
    uid = models.CharField(max_length=64, verbose_name='access_token', db_index=True)

    class Meta:
        db_table = 'tb_oauth_sina'
        verbose_name = 'sina登录用户数据'
        verbose_name_plural = verbose_name
