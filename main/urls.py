from django.urls import path, include

from main.appointments.views import AppointmentListCreateView
from main.category.views import CategoryViewSet
from main.organization.views import OrganizationViewSet
from .login import views
from rest_framework_simplejwt import views as jwt_views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/appointments', AppointmentListCreateView, basename='appointments')
router.register(r'api/organizations', OrganizationViewSet, basename='organizations')
router.register(r'api/categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', views.index, name='index'),
    path('api/validate/token/', views.ValidateToken.as_view(), name='ValidateToken'),
    path('api/me/', views.UserMeView.as_view(), name='user-me'),
    path('api/send/otp/', views.SendOTPView.as_view(), name='send-otp'),
    path('api/verify/otp/', views.VerifyOTPView.as_view(), name='verify-otp'),  # Add this line
    path('api/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', views.AuthenticateUser.as_view(), name='auth'),
    path('api/register/', views.RegisterUser.as_view(), name='register'),
    path('', include(router.urls)),
]