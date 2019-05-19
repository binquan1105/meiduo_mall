from django.conf.urls import url

from . import views

urlpatterns = [
    # 获取QQ登录界面url
    url(r'^qq/authorization/$', views.OAuthURLView.as_view()),

    # QQ登录成功后的回调处理
    #QQ登录成功后，返回一个/oauth_callback?code=26CAA7F3D904F3BCFBF84249A28F5807&state=%2F地址
    url(r'^oauth_callback/$', views.OAuthUserView.as_view()),

    #获取weibo授权登录链接
    url(r'^weibo/authorization/$', views.WeiBoOAuthUserView.as_view()),

    #获取微博登录授权code
    # oauth2/?code=645ce8eb81c67cddb54c8d7a0fb0e672
    url(r'^oauth2/$',views.GetWeiBoCode.as_view()),

    url(r'^oauth/sina/user/$',views.UnKnwoCode.as_view()),


]
