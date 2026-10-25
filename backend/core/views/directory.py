"""Users, departments and categories (reference data managed by administrators)."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Department, TicketCategory, AssetCategory
from ..permissions import IsAdmin, IsSupportStaff, IsAdminOrReadOnly, is_admin
from ..serializers import (UserSerializer, UserBriefSerializer, DepartmentSerializer,
                           TicketCategorySerializer, AssetCategorySerializer)

User = get_user_model()
NO_DELETE = ['get', 'post', 'put', 'patch', 'head', 'options']  # history must survive: deactivate instead of delete


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('department').order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'employee_id']
    filterset_fields = ['role', 'department', 'is_active']

    @action(detail=False, methods=['get'], permission_classes=[IsSupportStaff], pagination_class=None)
    def assignable(self, request):
        """Active people for assignment dropdowns. ?scope=agents -> support staff only, otherwise everyone."""
        qs = User.objects.filter(is_active=True).select_related('department').order_by('first_name', 'username')
        scope = request.query_params.get('scope')
        if scope == 'agents':
            qs = qs.filter(Q(role__in=['ADMIN', 'AGENT']) | Q(is_superuser=True))
        elif scope == 'employees':
            qs = qs.filter(role=User.Role.EMPLOYEE)
        return Response(UserBriefSerializer(qs, many=True).data)


class _ReferenceViewSet(viewsets.ModelViewSet):
    """Anyone signed in may read; only active rows for non-admins; only admins write."""
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs.model, 'is_active') and not is_admin(self.request.user):
            qs = qs.filter(is_active=True)
        return qs


class DepartmentViewSet(_ReferenceViewSet):
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer


class TicketCategoryViewSet(_ReferenceViewSet):
    queryset = TicketCategory.objects.all().order_by('name')
    serializer_class = TicketCategorySerializer


class AssetCategoryViewSet(_ReferenceViewSet):
    queryset = AssetCategory.objects.all().order_by('name')
    serializer_class = AssetCategorySerializer
