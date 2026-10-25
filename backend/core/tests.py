"""Backend tests for authentication, authorization, the ticket workflow, assets and dashboards.

Run from the backend folder:  pytest
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from .models import (Department, TicketCategory, AssetCategory, Asset, AssetHistory, Ticket, TicketHistory,
                     AssetAssignment, TicketComment, Notification)

User = get_user_model()
PW = 'StrongPass123!'


# ------------------------------------------------------------------ fixtures
@pytest.fixture
def dept(db):
    return Department.objects.create(name='IT')


@pytest.fixture
def category(db):
    return TicketCategory.objects.create(name='Network')


@pytest.fixture
def asset_category(db):
    return AssetCategory.objects.create(name='Laptop')


def make_user(username, role, dept=None):
    return User.objects.create_user(username=username, email=f'{username}@example.com', password=PW, role=role, department=dept)


@pytest.fixture
def admin(dept):
    return make_user('admin1', 'ADMIN', dept)


@pytest.fixture
def agent(dept):
    return make_user('agent1', 'AGENT', dept)


@pytest.fixture
def agent2(dept):
    return make_user('agent2', 'AGENT', dept)


@pytest.fixture
def emp(dept):
    return make_user('emp1', 'EMPLOYEE', dept)


@pytest.fixture
def emp2(dept):
    return make_user('emp2', 'EMPLOYEE', dept)


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def ticket(emp, category):
    return Ticket.objects.create(title='Laptop will not boot', description='It shows a black screen', category=category, created_by=emp)


def status_url(t):
    return f'/api/tickets/{t.id}/status/'


def do_status(user, t, new, **extra):
    return client_for(user).post(status_url(t), {'status': new, **extra}, format='json')


def results(resp):
    return resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data


# ------------------------------------------------------------------ authentication
def test_login_valid_and_invalid(emp):
    c = APIClient()
    ok = c.post('/api/auth/login/', {'username': 'emp1', 'password': PW}, format='json')
    assert ok.status_code == 200 and 'access' in ok.data
    bad = c.post('/api/auth/login/', {'username': 'emp1', 'password': 'wrong'}, format='json')
    assert bad.status_code == 401


def test_anonymous_cannot_access_protected_apis(db):
    c = APIClient()
    for url in ['/api/tickets/', '/api/assets/', '/api/users/', '/api/dashboard/admin/', '/api/notifications/', '/api/auth/me/']:
        assert c.get(url).status_code == 401, url


def test_deactivated_user_cannot_login_or_use_token(emp):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(emp).access_token)
    emp.is_active = False
    emp.save()
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    assert c.get('/api/tickets/').status_code == 401
    assert APIClient().post('/api/auth/login/', {'username': 'emp1', 'password': PW}, format='json').status_code == 401


def test_employee_string_false_is_not_treated_as_internal_note(emp, category):
    ticket = Ticket.objects.create(title='Public comment test', description='A valid description', category=category, created_by=emp)
    response = client_for(emp).post(f'/api/tickets/{ticket.id}/comments/', {
        'comment': 'This should be visible to the requester.', 'is_internal': 'false'
    }, format='json')
    assert response.status_code == 201
    assert response.data['is_internal'] is False


def test_register_disabled_by_default(db):
    r = APIClient().post('/api/auth/register/', {'username': 'x', 'email': 'x@e.com', 'password': PW}, format='json')
    assert r.status_code == 403


def test_register_creates_employee_only_when_enabled(db, settings):
    settings.ALLOW_PUBLIC_REGISTRATION = True
    r = APIClient().post('/api/auth/register/', {'username': 'newp', 'email': 'n@e.com', 'password': PW, 'role': 'ADMIN'}, format='json')
    assert r.status_code == 201
    assert User.objects.get(username='newp').role == 'EMPLOYEE'


def test_superuser_is_always_admin(db):
    su = User.objects.create_superuser(username='root', email='root@example.com', password=PW)
    assert su.role == 'ADMIN'
    assert client_for(su).get('/api/auth/me/').data['role'] == 'ADMIN'


def test_me_returns_role(agent):
    r = client_for(agent).get('/api/auth/me/')
    assert r.status_code == 200 and r.data['role'] == 'AGENT' and 'password' not in r.data


# ------------------------------------------------------------------ authorization
def test_employee_sees_only_own_tickets(emp, emp2, category):
    Ticket.objects.create(title='Mine mine', description='desc desc desc', category=category, created_by=emp)
    other = Ticket.objects.create(title='Theirs ok', description='desc desc desc', category=category, created_by=emp2)
    r = client_for(emp).get('/api/tickets/')
    assert len(results(r)) == 1
    assert client_for(emp).get(f'/api/tickets/{other.id}/').status_code == 404


def test_employee_cannot_manage_users_or_roles(emp, emp2):
    c = client_for(emp)
    assert c.get('/api/users/').status_code == 403
    assert c.patch(f'/api/users/{emp.id}/', {'role': 'ADMIN'}, format='json').status_code == 403
    assert c.post('/api/users/', {'username': 'z', 'password': PW}, format='json').status_code == 403


def test_agent_cannot_use_admin_endpoints(agent, emp):
    c = client_for(agent)
    assert c.get('/api/users/').status_code == 403
    assert c.patch(f'/api/users/{emp.id}/', {'role': 'ADMIN'}, format='json').status_code == 403
    assert c.get('/api/dashboard/admin/').status_code == 403
    assert c.post('/api/departments/', {'name': 'Hack'}, format='json').status_code == 403


def test_employee_cannot_use_agent_or_admin_dashboard(emp):
    c = client_for(emp)
    assert c.get('/api/dashboard/admin/').status_code == 403
    assert c.get('/api/dashboard/agent/').status_code == 403
    assert c.get('/api/dashboard/employee/').status_code == 200


def test_admin_cannot_change_own_role_or_deactivate_self(admin):
    c = client_for(admin)
    assert c.patch(f'/api/users/{admin.id}/', {'role': 'EMPLOYEE'}, format='json').status_code == 400
    assert c.patch(f'/api/users/{admin.id}/', {'is_active': False}, format='json').status_code == 400


def test_admin_creates_user_without_exposing_password(admin, dept):
    r = client_for(admin).post('/api/users/', {'username': 'fresh', 'email': 'f@e.com', 'password': PW,
                                               'role': 'AGENT', 'department': dept.id, 'employee_id': ''}, format='json')
    assert r.status_code == 201 and 'password' not in r.data
    assert User.objects.get(username='fresh').check_password(PW)


def test_tickets_and_assets_cannot_be_deleted(admin, ticket):
    assert client_for(admin).delete(f'/api/tickets/{ticket.id}/').status_code == 405


# ------------------------------------------------------------------ ticket creation
def test_ticket_creation_uses_authenticated_user_and_ignores_privileged_fields(emp, agent, category, dept):
    r = client_for(emp).post('/api/tickets/', {
        'title': 'Printer is jammed', 'description': 'Paper stuck in tray two', 'category': category.id,
        'priority': 'HIGH', 'created_by': agent.id, 'assigned_agent': agent.id, 'status': 'RESOLVED', 'department': 999,
    }, format='json')
    assert r.status_code == 201
    t = Ticket.objects.get(pk=r.data['id'])
    assert t.created_by == emp and t.assigned_agent is None and t.status == 'NEW' and t.department == dept
    assert t.ticket_number.startswith('HD-')
    assert TicketHistory.objects.filter(ticket=t, action='Created', actor=emp).count() == 1


def test_ticket_validation_and_inactive_category(emp, category):
    c = client_for(emp)
    assert c.post('/api/tickets/', {'title': 'x', 'description': 'short', 'category': category.id}, format='json').status_code == 400
    category.is_active = False
    category.save()
    r = c.post('/api/tickets/', {'title': 'Valid title', 'description': 'Long enough description', 'category': category.id}, format='json')
    assert r.status_code == 400 and 'category' in r.data


def test_ticket_numbers_are_unique(emp, category):
    nums = {Ticket.objects.create(title='abcde', description='x' * 12, category=category, created_by=emp).ticket_number for _ in range(30)}
    assert len(nums) == 30


def test_employee_can_only_link_own_asset(emp, emp2, category, asset_category):
    mine = Asset.objects.create(asset_tag='A1', category=asset_category, status='ASSIGNED', assigned_to=emp)
    theirs = Asset.objects.create(asset_tag='A2', category=asset_category, status='ASSIGNED', assigned_to=emp2)
    payload = {'title': 'Laptop broken', 'description': 'Screen flickers a lot', 'category': category.id}
    c = client_for(emp)
    assert c.post('/api/tickets/', {**payload, 'asset': theirs.id}, format='json').status_code == 400
    assert c.post('/api/tickets/', {**payload, 'asset': mine.id}, format='json').status_code == 201


def test_employee_cannot_edit_ticket(emp, ticket):
    assert client_for(emp).patch(f'/api/tickets/{ticket.id}/', {'priority': 'CRITICAL'}, format='json').status_code == 403


def test_agent_edit_priority_creates_history_but_not_title(agent, ticket):
    c = client_for(agent)
    assert c.patch(f'/api/tickets/{ticket.id}/', {'title': 'Changed title'}, format='json').status_code == 403
    r = c.patch(f'/api/tickets/{ticket.id}/', {'priority': 'CRITICAL'}, format='json')
    assert r.status_code == 200 and r.data['priority'] == 'CRITICAL'
    assert TicketHistory.objects.filter(ticket=ticket, action='Priority changed').exists()


# ------------------------------------------------------------------ assignment
def test_employee_cannot_assign(emp, agent, ticket):
    assert client_for(emp).post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent.id}, format='json').status_code == 403


def test_agent_takes_unassigned_ticket_only_for_self(agent, agent2, ticket):
    c = client_for(agent)
    assert c.post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent2.id}, format='json').status_code == 403
    r = c.post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent.id}, format='json')
    assert r.status_code == 200 and r.data['status'] == 'ASSIGNED' and r.data['assigned_agent'] == agent.id
    assert TicketHistory.objects.filter(ticket=ticket, action='Assigned').exists()
    assert TicketHistory.objects.filter(ticket=ticket, action='Status changed').exists()


def test_other_agent_cannot_take_over_assigned_ticket(agent, agent2, ticket):
    client_for(agent).post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent.id}, format='json')
    # the ticket belongs to agent1, so for agent2 it is not even visible (404)
    assert client_for(agent2).post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent2.id}, format='json').status_code == 404
    assert client_for(agent2).get(f'/api/tickets/{ticket.id}/').status_code == 404


def test_admin_can_reassign_and_notifies(admin, agent, agent2, ticket):
    c = client_for(admin)
    c.post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent.id}, format='json')
    r = c.post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent2.id}, format='json')
    assert r.status_code == 200 and r.data['assigned_agent'] == agent2.id
    assert TicketHistory.objects.filter(ticket=ticket, action='Reassigned').exists()
    assert Notification.objects.filter(recipient=agent2, ticket=ticket).exists()


def test_cannot_assign_to_employee_or_inactive(admin, emp, agent, ticket):
    c = client_for(admin)
    assert c.post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': emp.id}, format='json').status_code == 400
    agent.is_active = False
    agent.save()
    assert c.post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent.id}, format='json').status_code == 400


# ------------------------------------------------------------------ status workflow
@pytest.fixture
def assigned(ticket, agent):
    client_for(agent).post(f'/api/tickets/{ticket.id}/assign/', {'agent_id': agent.id}, format='json')
    ticket.refresh_from_db()
    return ticket


def test_employee_has_no_transitions_on_new_ticket(emp, ticket):
    r = client_for(emp).get(f'/api/tickets/{ticket.id}/')
    assert r.data['allowed_transitions'] == []
    assert do_status(emp, ticket, 'ASSIGNED').status_code == 400  # needs an agent first


def test_employee_cannot_change_status_directly(emp, assigned):
    assert do_status(emp, assigned, 'IN_PROGRESS').status_code == 403
    assert do_status(emp, assigned, 'RESOLVED').status_code == 400  # invalid transition


def test_invalid_transition_rejected(agent, assigned):
    r = do_status(agent, assigned, 'CLOSED')
    assert r.status_code == 400 and 'Invalid transition' in r.data['detail']
    assert do_status(agent, assigned, 'NOPE').status_code == 400


def test_other_agent_cannot_change_status(agent2, assigned):
    assert do_status(agent2, assigned, 'IN_PROGRESS').status_code == 404


def test_full_happy_path_with_history(agent, emp, assigned):
    assert do_status(agent, assigned, 'IN_PROGRESS').status_code == 200
    assert do_status(agent, assigned, 'PENDING', reason='Waiting for part').status_code == 200
    assert do_status(agent, assigned, 'IN_PROGRESS').status_code == 200
    r = do_status(agent, assigned, 'RESOLVED', resolution_notes='Replaced the SSD')
    assert r.status_code == 200 and r.data['resolved_at'] and r.data['resolution_notes'] == 'Replaced the SSD'
    assert r.data['allowed_transitions'] == ['CLOSED', 'REOPENED']
    assert client_for(emp).get(f'/api/tickets/{assigned.id}/').data['allowed_transitions'] == ['CLOSED', 'REOPENED']
    assert do_status(emp, assigned, 'CLOSED').status_code == 200
    changes = TicketHistory.objects.filter(ticket=assigned, action='Status changed').count()
    assert changes == 1 + 5  # ASSIGNED via assign + five status changes


def test_resolve_requires_notes_and_pending_requires_reason(agent, assigned):
    do_status(agent, assigned, 'IN_PROGRESS')
    before = TicketHistory.objects.filter(ticket=assigned).count()
    assert do_status(agent, assigned, 'RESOLVED').status_code == 400
    assert do_status(agent, assigned, 'PENDING').status_code == 400
    assigned.refresh_from_db()
    assert assigned.status == 'IN_PROGRESS' and assigned.resolved_at is None
    assert TicketHistory.objects.filter(ticket=assigned).count() == before  # failed change leaves no history


def test_owner_can_reopen_with_reason_and_clears_resolved_at(agent, emp, assigned):
    do_status(agent, assigned, 'IN_PROGRESS')
    do_status(agent, assigned, 'RESOLVED', resolution_notes='Done')
    assert do_status(emp, assigned, 'REOPENED').status_code == 400  # reason required
    r = do_status(emp, assigned, 'REOPENED', reason='Still broken')
    assert r.status_code == 200 and r.data['resolved_at'] is None and r.data['status'] == 'REOPENED'


def test_other_employee_cannot_close(emp2, agent, assigned):
    do_status(agent, assigned, 'IN_PROGRESS')
    do_status(agent, assigned, 'RESOLVED', resolution_notes='Done')
    assert do_status(emp2, assigned, 'CLOSED').status_code == 404


def test_closed_ticket_cannot_be_edited_or_commented(admin, emp, agent, assigned):
    do_status(agent, assigned, 'IN_PROGRESS')
    do_status(agent, assigned, 'RESOLVED', resolution_notes='Done')
    do_status(emp, assigned, 'CLOSED')
    assert client_for(admin).patch(f'/api/tickets/{assigned.id}/', {'priority': 'LOW'}, format='json').status_code == 400
    assert client_for(emp).post(f'/api/tickets/{assigned.id}/comments/', {'comment': 'hello'}, format='json').status_code == 400


# ------------------------------------------------------------------ comments
def test_employees_never_see_internal_notes(agent, emp, assigned):
    ca = client_for(agent)
    assert ca.post(f'/api/tickets/{assigned.id}/comments/', {'comment': 'secret diagnosis', 'is_internal': True}, format='json').status_code == 201
    assert ca.post(f'/api/tickets/{assigned.id}/comments/', {'comment': 'We are on it'}, format='json').status_code == 201
    seen = client_for(emp).get(f'/api/tickets/{assigned.id}/comments/').data
    assert [c['comment'] for c in seen] == ['We are on it']
    assert len(ca.get(f'/api/tickets/{assigned.id}/comments/').data) == 2
    # internal notes do not appear in history that employees can read
    assert not any('secret' in h['details'] for h in client_for(emp).get(f'/api/tickets/{assigned.id}/history/').data)


def test_employee_cannot_post_internal_note(emp, ticket):
    r = client_for(emp).post(f'/api/tickets/{ticket.id}/comments/', {'comment': 'note', 'is_internal': True}, format='json')
    assert r.status_code == 403 and TicketComment.objects.count() == 0


def test_comment_notifies_other_party(agent, emp, assigned):
    client_for(emp).post(f'/api/tickets/{assigned.id}/comments/', {'comment': 'Any update?'}, format='json')
    assert Notification.objects.filter(recipient=agent, message__contains='New comment').exists()


def test_notifications_are_private(emp, agent):
    Notification.objects.create(recipient=emp, message='for emp')
    assert len(results(client_for(agent).get('/api/notifications/'))) == 0
    assert len(results(client_for(emp).get('/api/notifications/'))) == 1


# ------------------------------------------------------------------ assets
@pytest.fixture
def laptop(asset_category):
    return Asset.objects.create(asset_tag='LAP-001', name='Dell Latitude', category=asset_category)


def test_asset_tag_unique(admin, asset_category, laptop):
    r = client_for(admin).post('/api/assets/', {'asset_tag': 'LAP-001', 'category': asset_category.id}, format='json')
    assert r.status_code == 400


def test_only_admin_manages_inventory(agent, emp, asset_category, laptop):
    for user in (agent, emp):
        c = client_for(user)
        assert c.post('/api/assets/', {'asset_tag': 'X', 'category': asset_category.id}, format='json').status_code == 403
        assert c.patch(f'/api/assets/{laptop.id}/', {'notes': 'hack'}, format='json').status_code in (403, 404)
        assert c.put(f'/api/assets/{laptop.id}/', {}, format='json').status_code in (403, 405)
        assert c.post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json').status_code in (403, 404)
        assert c.delete(f'/api/assets/{laptop.id}/').status_code in (403, 405)


def test_asset_status_and_owner_not_writable_via_patch(admin, emp, laptop):
    r = client_for(admin).patch(f'/api/assets/{laptop.id}/', {'status': 'ASSIGNED', 'assigned_to': emp.id}, format='json')
    assert r.status_code == 200
    laptop.refresh_from_db()
    assert laptop.status == 'AVAILABLE' and laptop.assigned_to is None


def test_assign_return_reassign_preserves_history(admin, emp, emp2, laptop):
    c = client_for(admin)
    assert c.post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json').status_code == 201
    assert c.post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp2.id}, format='json').status_code == 409  # already assigned
    assert c.post(f'/api/assets/{laptop.id}/reassign/', {'employee_id': emp2.id}, format='json').status_code == 201
    laptop.refresh_from_db()
    assert laptop.assigned_to == emp2 and laptop.status == 'ASSIGNED'
    assert AssetAssignment.objects.filter(asset=laptop).count() == 2
    assert AssetAssignment.objects.filter(asset=laptop, returned_at__isnull=True).count() == 1
    assert c.post(f'/api/assets/{laptop.id}/return/', format='json').status_code == 200
    laptop.refresh_from_db()
    assert laptop.status == 'AVAILABLE' and laptop.assigned_to is None
    assert AssetAssignment.objects.filter(asset=laptop).count() == 2  # nothing deleted
    assert c.post(f'/api/assets/{laptop.id}/return/', format='json').status_code == 409
    assert len(c.get(f'/api/assets/{laptop.id}/assignments/').data) == 2


def test_retired_and_maintenance_assets_cannot_be_assigned(admin, emp, laptop):
    c = client_for(admin)
    rec = {'maintenance_type': 'Repair', 'description': 'Fan noise', 'maintenance_date': '2026-10-20', 'cost': '10.00', 'result': 'OPEN'}
    assert c.post(f'/api/assets/{laptop.id}/maintenance/', rec, format='json').status_code == 201
    laptop.refresh_from_db()
    assert laptop.status == 'MAINTENANCE'
    assert c.post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json').status_code == 409
    assert c.post(f'/api/assets/{laptop.id}/complete-maintenance/', format='json').status_code == 200
    assert c.post(f'/api/assets/{laptop.id}/retire/', format='json').status_code == 200
    assert c.post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json').status_code == 409
    assert c.patch(f'/api/assets/{laptop.id}/', {'notes': 'x'}, format='json').status_code == 409


def test_cannot_retire_assigned_or_service_assigned_asset(admin, emp, laptop):
    c = client_for(admin)
    c.post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json')
    assert c.post(f'/api/assets/{laptop.id}/retire/', format='json').status_code == 409
    rec = {'maintenance_type': 'Repair', 'description': 'x', 'maintenance_date': '2026-10-20', 'result': 'OPEN'}
    assert c.post(f'/api/assets/{laptop.id}/maintenance/', rec, format='json').status_code == 409


def test_employee_sees_only_own_assets_without_price(emp, emp2, admin, asset_category, laptop):
    client_for(admin).post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json')
    Asset.objects.create(asset_tag='OTHER', category=asset_category)
    r = client_for(emp).get('/api/assets/')
    assert len(results(r)) == 1 and 'purchase_price' not in results(r)[0] and 'notes' not in results(r)[0]
    assert client_for(emp2).get(f'/api/assets/{laptop.id}/').status_code == 404
    assert client_for(emp).get(f'/api/assets/{laptop.id}/assignments/').status_code == 403


def test_assignment_creates_notification(admin, emp, laptop):
    client_for(admin).post(f'/api/assets/{laptop.id}/assign/', {'employee_id': emp.id}, format='json')
    assert Notification.objects.filter(recipient=emp, asset=laptop).exists()


# ------------------------------------------------------------------ dashboards
def test_empty_dashboards_are_valid(admin, agent, emp):
    for user, path in ((admin, 'admin'), (agent, 'agent'), (emp, 'employee')):
        r = client_for(user).get(f'/api/dashboard/{path}/')
        assert r.status_code == 200 and r.data['total_tickets'] == 0 and r.data['tickets_by_status'] == []




def test_asset_history_records_create_and_condition_changes(admin, asset_category, laptop):
    c = client_for(admin)
    # The fixture creates the asset directly, so exercise API condition actions here.
    assert c.post(f'/api/assets/{laptop.id}/mark-damaged/').status_code == 200
    laptop.refresh_from_db()
    assert laptop.status == Asset.Status.DAMAGED
    assert AssetHistory.objects.filter(asset=laptop, action='Asset marked damaged', actor=admin).exists()
    assert c.post(f'/api/assets/{laptop.id}/recover/').status_code == 200
    laptop.refresh_from_db()
    assert laptop.status == Asset.Status.AVAILABLE
    assert AssetHistory.objects.filter(asset=laptop, action='Asset recovered').exists()


def test_asset_history_is_visible_to_support_staff_only(admin, agent, emp, asset_category, laptop):
    c = client_for(admin)
    created = c.post('/api/assets/', {'asset_tag': 'AUDIT-1', 'name': 'Audit asset', 'category': asset_category.id}, format='json')
    assert created.status_code == 201
    asset_id = created.data['id']
    assert client_for(agent).get(f'/api/assets/{asset_id}/history/').status_code == 200
    assert client_for(emp).get(f'/api/assets/{asset_id}/history/').status_code == 403


def test_asset_assignment_rejects_support_staff(admin, agent, asset_category, laptop):
    response = client_for(admin).post(f'/api/assets/{laptop.id}/assign/', {'employee_id': agent.id}, format='json')
    assert response.status_code == 400
    laptop.refresh_from_db()
    assert laptop.status == Asset.Status.AVAILABLE


def test_asset_maintenance_history_can_be_read_by_agent(agent, admin, asset_category, laptop):
    client_for(admin).post(f'/api/assets/{laptop.id}/maintenance/', {
        'maintenance_type': 'Inspection', 'description': 'Check fan', 'maintenance_date': '2026-10-25',
        'cost': '0', 'result': 'COMPLETED'
    }, format='json')
    response = client_for(agent).get(f'/api/assets/{laptop.id}/maintenance/')
    assert response.status_code == 200


def test_asset_category_can_be_deactivated_and_is_returned_to_admin(admin, asset_category):
    response = client_for(admin).patch(f'/api/asset-categories/{asset_category.id}/', {'is_active': False}, format='json')
    assert response.status_code == 200
    assert client_for(admin).get('/api/asset-categories/').status_code == 200


def test_admin_dashboard_counts_match_database(admin, emp, category, asset_category):
    for status in ('NEW', 'NEW', 'IN_PROGRESS', 'RESOLVED'):
        Ticket.objects.create(title='abcde', description='x' * 12, category=category, created_by=emp, status=status)
    Asset.objects.create(asset_tag='A', category=asset_category)
    Asset.objects.create(asset_tag='B', category=asset_category, status='MAINTENANCE')
    d = client_for(admin).get('/api/dashboard/admin/').data
    assert (d['total_tickets'], d['new_tickets'], d['in_progress_tickets'], d['resolved_tickets']) == (4, 2, 1, 1)
    assert (d['total_assets'], d['available_assets'], d['maintenance_assets']) == (2, 1, 1)
    assert {r['status']: r['count'] for r in d['tickets_by_status']}['NEW'] == 2


def test_employee_dashboard_only_counts_own(emp, emp2, category):
    Ticket.objects.create(title='abcde', description='x' * 12, category=category, created_by=emp)
    Ticket.objects.create(title='abcde', description='x' * 12, category=category, created_by=emp2)
    assert client_for(emp).get('/api/dashboard/employee/').data['total_tickets'] == 1


def test_agent_dashboard_counts_assigned_and_queue(agent, emp, category):
    Ticket.objects.create(title='abcde', description='x' * 12, category=category, created_by=emp)
    Ticket.objects.create(title='abcde', description='x' * 12, category=category, created_by=emp, assigned_agent=agent, status='ASSIGNED')
    d = client_for(agent).get('/api/dashboard/agent/').data
    assert d['total_tickets'] == 1 and d['eligible_unassigned'] == 1


# ------------------------------------------------------------------ lists
def test_filters_search_and_priority_sort(admin, emp, category):
    for title, prio in (('Alpha ticket', 'LOW'), ('Bravo ticket', 'CRITICAL'), ('Charlie ticket', 'MEDIUM')):
        Ticket.objects.create(title=title, description='x' * 12, category=category, created_by=emp, priority=prio)
    c = client_for(admin)
    assert [t['title'] for t in results(c.get('/api/tickets/?ordering=-priority_rank'))][0] == 'Bravo ticket'
    assert len(results(c.get('/api/tickets/?search=Alpha'))) == 1
    assert len(results(c.get('/api/tickets/?unassigned=true'))) == 3
    assert len(results(c.get('/api/tickets/?priority=LOW'))) == 1


def test_pagination_shape(admin, emp, category):
    for i in range(12):
        Ticket.objects.create(title=f'Ticket {i:02}', description='x' * 12, category=category, created_by=emp)
    r = client_for(admin).get('/api/tickets/')
    assert r.data['count'] == 12 and len(r.data['results']) == 10 and r.data['next']


def test_non_admin_sees_only_active_categories(emp, category):
    TicketCategory.objects.create(name='Retired', is_active=False)
    names = [c['name'] for c in client_for(emp).get('/api/ticket-categories/').data]
    assert names == ['Network']
