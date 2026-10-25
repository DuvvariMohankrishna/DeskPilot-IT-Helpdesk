from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Notification
from ..serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """A user only ever sees their own notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related('ticket', 'asset')

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(is_read=False).count()})

    @extend_schema(request=None, responses=NotificationSerializer)
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        obj = self.get_object()
        obj.is_read = True
        obj.save(update_fields=['is_read'])
        return Response(NotificationSerializer(obj).data)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'updated': updated})
