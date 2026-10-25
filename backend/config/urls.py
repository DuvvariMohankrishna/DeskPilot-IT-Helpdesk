from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.views import LoginView, RegisterView, MeView
urlpatterns = [
 path('admin/', admin.site.urls),
 path('api/auth/register/', RegisterView.as_view(), name='register'),
 path('api/auth/login/', LoginView.as_view(), name='token_obtain_pair'),
 path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
 path('api/auth/me/', MeView.as_view(), name='me'),
 path('api/', include('core.urls')),
 path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
 path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
