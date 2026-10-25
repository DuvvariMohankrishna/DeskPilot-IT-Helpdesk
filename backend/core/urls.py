from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (UserViewSet, DepartmentViewSet, TicketCategoryViewSet, AssetCategoryViewSet, TicketViewSet,
                    AssetViewSet, NotificationViewSet, AdminDashboardView, AgentDashboardView, EmployeeDashboardView)

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('departments', DepartmentViewSet)
router.register('ticket-categories', TicketCategoryViewSet)
router.register('asset-categories', AssetCategoryViewSet)
router.register('tickets', TicketViewSet, basename='ticket')
router.register('assets', AssetViewSet, basename='asset')
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/admin/', AdminDashboardView.as_view()),
    path('dashboard/agent/', AgentDashboardView.as_view()),
    path('dashboard/employee/', EmployeeDashboardView.as_view()),
]
