from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..filters import TicketFilter
from ..models import Ticket, TicketComment, TicketHistory
from ..permissions import is_admin, is_agent, is_support_staff
from ..serializers import (TicketSerializer, TicketWriteSerializer, TicketCommentSerializer,
                           TicketHistorySerializer, display_name)
from .. import workflow
from ..workflow import notify

User = get_user_model()
S = Ticket.Status

PRIORITY_RANK = Case(
    When(priority='CRITICAL', then=Value(4)), When(priority='HIGH', then=Value(3)),
    When(priority='MEDIUM', then=Value(2)), default=Value(1), output_field=IntegerField(),
)


def log(ticket, actor, action_name, details=''):
    """Always uses the authenticated user as actor, never a value sent by the browser."""
    return TicketHistory.objects.create(ticket=ticket, actor=actor, action=action_name, details=details)


def err(message, code=400):
    return Response({'detail': message}, status=code)


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # tickets are never deleted (audit trail)
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TicketFilter
    search_fields = ['ticket_number', 'title']
    ordering_fields = ['created_at', 'updated_at', 'priority_rank']
    ordering = ['-created_at']

    def get_queryset(self):
        return (workflow.visible_tickets(self.request.user)
                .select_related('created_by', 'assigned_agent', 'category', 'asset', 'department')
                .annotate(priority_rank=PRIORITY_RANK))

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return TicketWriteSerializer
        return TicketSerializer

    def read(self, ticket):
        return TicketSerializer(ticket, context=self.get_serializer_context()).data

    # ------------------------------------------------------------ create / edit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            ticket = serializer.save(created_by=request.user, department=request.user.department, status=S.NEW)
            log(ticket, request.user, 'Created', f'Ticket created with {ticket.get_priority_display()} priority')
            notify(request.user, f'Your ticket {ticket.ticket_number} was created', ticket=ticket)
            for admin in User.objects.filter(Q(role='ADMIN') | Q(is_superuser=True), is_active=True).exclude(pk=request.user.pk):
                notify(admin, f'New ticket {ticket.ticket_number}: {ticket.title}', ticket=ticket)
        return Response(self.read(ticket), status=201)

    def partial_update(self, request, *args, **kwargs):
        ticket = self.get_object()
        user = request.user
        if not is_support_staff(user):
            return err('Employees cannot edit ticket fields. Add a comment instead.', 403)
        if ticket.status == S.CLOSED:
            return err('A closed ticket cannot be edited. Reopen it first.')
        if not workflow.can_edit(user, ticket):
            return err('This ticket is assigned to another agent.', 403)
        if is_agent(user) and {'title', 'description'} & set(request.data):
            return err('Only administrators can change the title or description.', 403)

        serializer = TicketWriteSerializer(ticket, data=request.data, partial=True, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        before = {'priority': ticket.priority, 'category': ticket.category.name,
                  'asset': ticket.asset.asset_tag if ticket.asset else None,
                  'title': ticket.title, 'description': ticket.description}
        with transaction.atomic():
            ticket = serializer.save()
            if before['priority'] != ticket.priority:
                log(ticket, user, 'Priority changed', f"{before['priority']} -> {ticket.priority}")
            if before['category'] != ticket.category.name:
                log(ticket, user, 'Category changed', f"{before['category']} -> {ticket.category.name}")
            new_asset = ticket.asset.asset_tag if ticket.asset else None
            if before['asset'] != new_asset:
                log(ticket, user, 'Related asset changed', f"{before['asset'] or 'none'} -> {new_asset or 'none'}")
            if before['title'] != ticket.title or before['description'] != ticket.description:
                log(ticket, user, 'Details edited', 'Title or description was updated')
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(self.read(ticket))

    # ------------------------------------------------------------ assignment
    @extend_schema(request=inline_serializer('AssignTicket', {'agent_id': serializers.IntegerField()}), responses=TicketSerializer)
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        user = request.user
        if not is_support_staff(user):
            return err('Only support staff can assign tickets.', 403)
        if ticket.status in (S.RESOLVED, S.CLOSED):
            return err('Resolved or closed tickets cannot be assigned. Reopen the ticket first.')
        if not workflow.can_assign(user, ticket):
            return err('You can only assign tickets that are unassigned or already yours.', 403)
        try:
            agent = User.objects.get(Q(role__in=['ADMIN', 'AGENT']) | Q(is_superuser=True), pk=request.data.get('agent_id'), is_active=True)
        except (User.DoesNotExist, TypeError, ValueError):
            return err('Provide a valid active support agent id.')
        if is_agent(user) and ticket.assigned_agent_id is None and agent.pk != user.pk:
            return err('Agents can only take unassigned tickets for themselves.', 403)
        if ticket.assigned_agent_id == agent.pk:
            return err('This ticket is already assigned to that agent.')

        with transaction.atomic():
            old = ticket.assigned_agent
            previous_status = ticket.status
            ticket.assigned_agent = agent
            if ticket.status in (S.NEW, S.REOPENED):
                ticket.status = S.ASSIGNED
            ticket.save()
            log(ticket, user, 'Reassigned' if old else 'Assigned',
                f'Assigned to {display_name(agent)}' + (f' (was {display_name(old)})' if old else ''))
            if previous_status != ticket.status:
                log(ticket, user, 'Status changed', f'{previous_status} -> {ticket.status}')
            if agent.pk != user.pk:
                notify(agent, f'{ticket.ticket_number} was assigned to you', ticket=ticket)
            if old and old.pk not in (user.pk, agent.pk):
                notify(old, f'{ticket.ticket_number} was reassigned to {display_name(agent)}', ticket=ticket)
            if ticket.created_by_id != user.pk:
                notify(ticket.created_by, f'{ticket.ticket_number} is now handled by {display_name(agent)}', ticket=ticket)
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(self.read(ticket))

    # ------------------------------------------------------------ status workflow
    @extend_schema(request=inline_serializer('ChangeTicketStatus', {'status': serializers.CharField(), 'reason': serializers.CharField(required=False), 'resolution_notes': serializers.CharField(required=False)}), responses=TicketSerializer)
    @action(detail=True, methods=['post'], url_path='status')
    def change_status(self, request, pk=None):
        ticket = self.get_object()
        user = request.user
        new = request.data.get('status')
        notes = (request.data.get('resolution_notes') or '').strip()
        reason = (request.data.get('reason') or '').strip()

        if new not in Ticket.Status.values:
            return err('Choose a valid status.')
        if new not in workflow.TRANSITIONS.get(ticket.status, []):
            return err(f'Invalid transition: {ticket.status} -> {new}.')
        if new == S.ASSIGNED and not ticket.assigned_agent_id:
            return err('Assign an agent first.')
        if new not in workflow.allowed_transitions(user, ticket):
            return err('You are not allowed to make this status change.', 403)
        if new in workflow.REASON_REQUIRED and not reason:
            return err(workflow.REASON_REQUIRED[new])
        if new in workflow.NOTES_REQUIRED and not notes:
            return err(workflow.NOTES_REQUIRED[new])

        with transaction.atomic():
            previous = ticket.status
            ticket.status = new
            if new == S.RESOLVED:
                ticket.resolution_notes = notes
                ticket.resolved_at = timezone.now()
            elif new == S.REOPENED:
                ticket.resolved_at = None
            ticket.save()
            extra = reason or notes
            log(ticket, user, 'Status changed', f'{previous} -> {new}' + (f': {extra}' if extra else ''))
            label = ticket.get_status_display()
            for person in {ticket.created_by, ticket.assigned_agent}:
                if person and person.pk != user.pk:
                    notify(person, f'{ticket.ticket_number} status changed to {label}', ticket=ticket)
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(self.read(ticket))

    # ------------------------------------------------------------ comments and history
    @extend_schema(request=TicketCommentSerializer, responses=TicketCommentSerializer(many=True))
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        user = request.user
        if request.method == 'GET':
            qs = ticket.comments.select_related('author')
            if not is_support_staff(user):
                qs = qs.filter(is_internal=False)  # employees never see internal support notes
            return Response(TicketCommentSerializer(qs, many=True).data)

        if ticket.status == S.CLOSED:
            return err('This ticket is closed. Reopen it to add comments.')
        serializer = TicketCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        internal = serializer.validated_data.get('is_internal', False)
        if internal and not is_support_staff(user):
            return err('Only support staff can add internal notes.', 403)
        with transaction.atomic():
            comment = serializer.save(ticket=ticket, author=user, is_internal=internal)
            if not internal:
                log(ticket, user, 'Comment added', 'A comment was added')
                for person in {ticket.created_by, ticket.assigned_agent}:
                    if person and person.pk != user.pk:
                        notify(person, f'New comment on {ticket.ticket_number}', ticket=ticket)
        return Response(TicketCommentSerializer(comment).data, status=201)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        ticket = self.get_object()
        return Response(TicketHistorySerializer(ticket.history.select_related('actor'), many=True).data)
