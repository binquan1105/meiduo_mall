from django.conf.urls import url

from . import views

urlpatterns = [
    #提交订单
    url(r'^orders/commit/$',views.OrderCommitView.as_view()),
    # 订单成功界面
    url(r'^orders/success/$', views.OrderSuccessView.as_view()),
    #待评价
    url(r'^orders/comment/$', views.OrderCommentView.as_view()),

]