from django.conf.urls import url

from . import views

urlpatterns = [
    #支付链接
    url(r'^payment/(?P<order_id>\d+)/$',views.PaymentView.as_view()),
    #支付成功后跳转的回调页面
    url(r'^payment/status/$',views.PaymentStatusView.as_view()),


]