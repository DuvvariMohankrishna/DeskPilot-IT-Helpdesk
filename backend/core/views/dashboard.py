"""Role-specific dashboards. Every number comes from permission-filtered querysets, never constants."""
from django.db.models import Count, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Asset, Ticket, TicketHistory
from ..permissions import IsAdmin, is_admin
from ..serializers import TicketSerializer, AssetSerializer, TicketHistorySerializer
from ..permissions import IsSupportStaff, is_agent
from .. import workflow

S = Ticket.Status


def group(qs, field):
    return [{field: row[field], 'count': row['count']} for row in qs.values(field).annotate(count=Count('id')).order_by(field)]


def ticket_block(tickets):
    return {
        'total_tickets': tickets.count(),
        'new_tickets': tickets.filter(status=S.NEW).count(),
        'unassigned_tickets': tickets.filter(assigned_agent__isnull=True).exclude(status__in=[S.RESOLVED, S.CLOSED]).count(),
        'open_tickets': tickets.filter(status__in=workflow.OPEN_STATUSES).count(),
        'in_progress_tickets': tickets.filter(status=S.IN_PROGRESS).count(),
        'pending_tickets': tickets.filter(status=S.PENDING).count(),
        'resolved_tickets': tickets.filter(status=S.RESOLVED).count(),
        'closed_tickets': tickets.filter(status=S.CLOSED).count(),
        'critical_tickets': tickets.filter(priority='CRITICAL').exclude(status__in=[S.RESOLVED, S.CLOSED]).count(),
        'tickets_by_status': group(tickets, 'status'),
        'tickets_by_priority': group(tickets, 'priority'),
    }


def with_category(tickets):
    rows = tickets.values('category__name').annotate(count=Count('id')).order_by('category__name')
    return [{'category': r['category__name'], 'count': r['count']} for r in rows]


def recent(tickets, request, limit=5):
    qs = tickets.select_related('created_by', 'assigned_agent', 'category', 'asset', 'department').order_by('-updated_at')[:limit]
    return TicketSerializer(qs, many=True, context={'request': request}).data


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        tickets = Ticket.objects.all()
        assets = Asset.objects.all()
        data = ticket_block(tickets)
        data.update({
            'role': 'ADMIN',
            'tickets_by_category': with_category(tickets),
            'total_assets': assets.count(),
            'available_assets': assets.filter(status='AVAILABLE').count(),
            'assigned_assets': assets.filter(status='ASSIGNED').count(),
            'maintenance_assets': assets.filter(status='MAINTENANCE').count(),
            'assets_by_status': group(assets, 'status'),
            'recent_tickets': recent(tickets, request),
            'recent_activity': TicketHistorySerializer(
                TicketHistory.objects.select_related('actor', 'ticket').order_by('-created_at')[:8], many=True).data,
        })
        return Response(data)


class AgentDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsSupportStaff]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user
        mine = Ticket.objects.filter(assigned_agent=user)
        unassigned = Ticket.objects.filter(assigned_agent__isnull=True, status__in=[S.NEW, S.REOPENED])
        data = ticket_block(mine)
        data.update({
            'role': 'AGENT',
            'eligible_unassigned': unassigned.count(),
            'needs_attention': mine.filter(priority__in=['HIGH', 'CRITICAL']).exclude(status__in=[S.RESOLVED, S.CLOSED]).count(),
            'tickets_by_category': with_category(mine),
            'recent_tickets': recent(mine, request),
            'unassigned_queue': recent(unassigned, request),
            'recently_resolved': recent(mine.filter(status__in=[S.RESOLVED, S.CLOSED]), request),
        })
        return Response(data)


class EmployeeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user
        mine = Ticket.objects.filter(created_by=user)
        assets = Asset.objects.filter(assigned_to=user).select_related('category')
        data = ticket_block(mine)
        data.update({
            'role': 'EMPLOYEE',
            'tickets_by_category': with_category(mine),
            'total_assets': assets.count(),
            'my_assets': AssetSerializer(assets[:5], many=True, context={'request': request}).data,
            'recent_tickets': recent(mine, request),
        })
        return Response(data)
