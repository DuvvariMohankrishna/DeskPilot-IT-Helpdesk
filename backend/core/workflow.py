"""Ticket workflow rules, in ONE place, used by the API, serializers and tests.

The serializer exposes `allowed_transitions` to React, so the dropdown can never offer
something the backend would reject.
"""
from django.db.models import Q

from .models import Ticket, Notification
from .permissions import is_admin, is_agent, is_support_staff

S = Ticket.Status

# current status -> statuses it may move to
TRANSITIONS = {
    S.NEW: [S.ASSIGNED],
    S.ASSIGNED: [S.IN_PROGRESS, S.PENDING],
    S.IN_PROGRESS: [S.PENDING, S.RESOLVED],
    S.PENDING: [S.IN_PROGRESS, S.RESOLVED],
    S.RESOLVED: [S.CLOSED, S.REOPENED],
    S.CLOSED: [S.REOPENED],
    S.REOPENED: [S.ASSIGNED, S.IN_PROGRESS],
}

# The ticket owner (typically an employee) may only do these moves.
OWNER_TRANSITIONS = {(S.RESOLVED, S.CLOSED), (S.RESOLVED, S.REOPENED), (S.CLOSED, S.REOPENED)}

REASON_REQUIRED = {S.PENDING: 'A reason is required to put a ticket on hold.',
                   S.REOPENED: 'A reason is required to reopen a ticket.'}
NOTES_REQUIRED = {S.RESOLVED: 'Resolution notes are required to resolve a ticket.'}

OPEN_STATUSES = [S.NEW, S.ASSIGNED, S.IN_PROGRESS, S.PENDING, S.REOPENED]


def visible_tickets(user):
    """Which tickets a user may see at all."""
    qs = Ticket.objects.all()
    if is_admin(user):
        return qs
    if is_agent(user):
        # assigned to me, still unassigned (eligible to take), or created by me
        return qs.filter(Q(assigned_agent=user) | Q(assigned_agent__isnull=True) | Q(created_by=user))
    return qs.filter(created_by=user)


def is_working_agent(user, ticket):
    """Admin, or the agent who currently owns the ticket."""
    return is_admin(user) or (is_agent(user) and ticket.assigned_agent_id == user.id)


def allowed_transitions(user, ticket):
    result = []
    for nxt in TRANSITIONS.get(ticket.status, []):
        if nxt == S.ASSIGNED and not ticket.assigned_agent_id:
            continue  # moving to ASSIGNED happens through the assign action, which needs an agent
        by_owner = ticket.created_by_id == user.id and (ticket.status, nxt) in OWNER_TRANSITIONS
        if is_working_agent(user, ticket) or by_owner:
            result.append(nxt)
    return result


def can_assign(user, ticket):
    if ticket.status in (S.RESOLVED, S.CLOSED):
        return False
    if is_admin(user):
        return True
    return is_agent(user) and ticket.assigned_agent_id in (None, user.id)


def can_edit(user, ticket):
    if ticket.status == S.CLOSED:
        return False
    if is_admin(user):
        return True
    return is_agent(user) and ticket.assigned_agent_id in (None, user.id)


def notify(recipient, message, ticket=None, asset=None):
    if recipient is not None and recipient.is_active:
        Notification.objects.create(recipient=recipient, message=message, ticket=ticket, asset=asset)
