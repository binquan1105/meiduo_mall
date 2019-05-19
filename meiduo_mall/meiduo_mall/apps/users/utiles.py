from django.contrib.auth.backends import ModelBackend
import re
from .models import User
def get_user_password(account):
    """
        根据用户名或手机号来查询user
        :param account: 手机号 、 用户名
        :return: None, user
        """
    try:
        #判断account是手机号还是用户名
        if re.match('^1[3-9]\d{9}',account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    #get()获取不到结果会引发User.DoesNotExist异常
    except User.DoesNotExist:
        return None
    else:
        return user

# 自定义django的验证后端类
class UserMobile(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 根据手机号或者用户名检查user
        user = get_user_password(username)
        # 检查密码是否正确
        if user and user.check_password(password):
            return user


# 在全局配置指定认证后端
# 指定自定义的用户认证后端
# AUTHENTICATION_BACKENDS = ['users.utiles.UserMobile']