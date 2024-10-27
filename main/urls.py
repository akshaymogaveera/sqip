from django.urls import path, include

from main.appointments.views import AppointmentListCreateView, OrganizationListCreateView
from .login import views
from rest_framework_simplejwt import views as jwt_views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/appointments', AppointmentListCreateView, basename='appointments')

urlpatterns = [
    path('', views.index, name='index'),
    path('api/validate/token/', views.ValidateToken.as_view(), name='ValidateToken'),
    path('api/send/otp/', views.sendSms.as_view(), name='send-otp'),
    path('api/validate/otp/', views.verifySms.as_view(), name='validate-otp'),
    path('api/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', views.AuthenticateUser.as_view(), name='auth'),  # Get Auth token using username
    path('api/organizations/', OrganizationListCreateView.as_view(), name='organization-list-create'),
    path('', include(router.urls)),
]