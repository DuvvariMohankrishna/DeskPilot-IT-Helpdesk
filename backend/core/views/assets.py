from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..filters import AssetFilter
from ..models import Asset, AssetAssignment, AssetMaintenance, AssetHistory
from ..permissions import IsAdmin, IsSupportStaff, is_support_staff
from ..serializers import AssetSerializer, AssetAssignmentSerializer, AssetMaintenanceSerializer, AssetHistorySerializer, display_name
from ..workflow import notify

User = get_user_model()
A = Asset.Status


def err(message, code=400):
    return Response({'detail': message}, status=code)


class AssetViewSet(viewsets.ModelViewSet):
    """Inventory. Admins manage everything; agents read; employees see only assets assigned to them."""
    serializer_class = AssetSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # assets are retired, never deleted
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AssetFilter
    search_fields = ['asset_tag', 'name', 'serial_number', 'manufacturer', 'model_name']
    ordering_fields = ['created_at', 'warranty_expiry', 'asset_tag']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action in ('assignments', 'history'):
            return [IsSupportStaff()]
        if self.action == 'maintenance' and self.request.method == 'GET':
            return [IsSupportStaff()]
        return [IsAdmin()]  # inventory mutations remain administrator-only

    def get_queryset(self):
        qs = Asset.objects.select_related('category', 'assigned_to', 'department')
        user = self.request.user
        return qs if is_support_staff(user) else qs.filter(assigned_to=user)

    def perform_create(self, serializer):
        asset = serializer.save()
        AssetHistory.objects.create(asset=asset, actor=self.request.user, action='Asset created',
                                    details=f'Asset {asset.asset_tag} was added to inventory.')

    def perform_update(self, serializer):
        instance = self.get_object()
        before = {field: getattr(instance, field) for field in ('name', 'serial_number', 'manufacturer', 'model_name', 'purchase_date', 'purchase_price', 'warranty_expiry', 'location', 'department_id', 'category_id', 'notes')}
        asset = serializer.save()
        changed = []
        for field, old in before.items():
            new = getattr(asset, field)
            if old != new:
                changed.append(f'{field}: {old if old is not None else "—"} → {new if new is not None else "—"}')
        if changed:
            AssetHistory.objects.create(asset=asset, actor=self.request.user, action='Asset details updated', details='; '.join(changed))

    def partial_update(self, request, *args, **kwargs):
        if self.get_object().status == A.RETIRED:
            return err('A retired asset cannot be edited.', 409)
        return super().partial_update(request, *args, **kwargs)

    def _locked(self, pk):
        return get_object_or_404(Asset.objects.select_for_update(), pk=pk)

    def _person(self, request):
        try:
            return User.objects.get(pk=request.data.get('employee_id'), is_active=True, role=User.Role.EMPLOYEE)
        except (User.DoesNotExist, TypeError, ValueError):
            return None

    def _ok(self, asset, extra=None, code=200):
        asset = self.get_queryset().get(pk=asset.pk)
        data = {'asset': AssetSerializer(asset, context=self.get_serializer_context()).data}
        data.update(extra or {})
        return Response(data, status=code)

    @extend_schema(request=inline_serializer('AssetPerson', {'employee_id': serializers.IntegerField(), 'reason': serializers.CharField(required=False)}), responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        employee = self._person(request)
        if employee is None:
            return err('Provide a valid active employee id.')
        with transaction.atomic():
            asset = self._locked(pk)
            if asset.status == A.RETIRED:
                return err('A retired asset cannot be assigned.', 409)
            if asset.status == A.MAINTENANCE:
                return err('An asset under maintenance cannot be assigned.', 409)
            if asset.status != A.AVAILABLE or asset.assigned_to_id:
                return err('Asset is not available for assignment.', 409)
            asset.assigned_to, asset.status = employee, A.ASSIGNED
            asset.save()
            assignment = AssetAssignment.objects.create(asset=asset, employee=employee, assigned_by=request.user,
                                                        reason=request.data.get('reason', '')[:250])
            AssetHistory.objects.create(asset=asset, actor=request.user, action='Asset assigned', details=f'Assigned to {display_name(employee)}. {assignment.reason}'.strip())
            notify(employee, f'Asset {asset.asset_tag} was assigned to you', asset=asset)
        return self._ok(asset, {'assignment': AssetAssignmentSerializer(assignment).data}, 201)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['post'], url_path='return')
    def return_asset(self, request, pk=None):
        with transaction.atomic():
            asset = self._locked(pk)
            assignment = asset.assignments.filter(returned_at__isnull=True).first()
            if not assignment or asset.status != A.ASSIGNED:
                return err('Asset has no active assignment.', 409)
            assignment.returned_at = timezone.now()
            assignment.save()
            asset.assigned_to, asset.status = None, A.AVAILABLE
            asset.save()
            AssetHistory.objects.create(asset=asset, actor=request.user, action='Asset returned', details=f'Returned by {display_name(assignment.employee)}.')
        return self._ok(asset)

    @extend_schema(request=inline_serializer('AssetPerson', {'employee_id': serializers.IntegerField(), 'reason': serializers.CharField(required=False)}), responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['post'])
    def reassign(self, request, pk=None):
        employee = self._person(request)
        if employee is None:
            return err('Provide a valid active employee id.')
        with transaction.atomic():
            asset = self._locked(pk)
            current = asset.assignments.filter(returned_at__isnull=True).first()
            if asset.status != A.ASSIGNED or not current:
                return err('Only an assigned asset can be reassigned.', 409)
            if current.employee_id == employee.pk:
                return err('The asset is already assigned to that person.')
            current.returned_at = timezone.now()  # keep the old row: history is preserved
            current.save()
            asset.assigned_to = employee
            asset.save()
            assignment = AssetAssignment.objects.create(asset=asset, employee=employee, assigned_by=request.user,
                                                        reason=request.data.get('reason', '')[:250])
            AssetHistory.objects.create(asset=asset, actor=request.user, action='Asset reassigned', details=f'From {display_name(current.employee)} to {display_name(employee)}. {assignment.reason}'.strip())
            notify(employee, f'Asset {asset.asset_tag} was assigned to you', asset=asset)
            notify(current.employee, f'Asset {asset.asset_tag} was reassigned to {display_name(employee)}', asset=asset)
        return self._ok(asset, {'assignment': AssetAssignmentSerializer(assignment).data}, 201)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        with transaction.atomic():
            asset = self._locked(pk)
            if asset.status == A.RETIRED:
                return err('Asset is already retired.', 409)
            if asset.status == A.ASSIGNED:
                return err('Return the asset before retiring it.', 409)
            asset.status = A.RETIRED
            asset.save()
            AssetHistory.objects.create(asset=asset, actor=request.user, action='Asset retired', details='Asset retired from active inventory.')
        return self._ok(asset)

    @extend_schema(request=AssetMaintenanceSerializer, responses=AssetMaintenanceSerializer(many=True))
    @action(detail=True, methods=['get', 'post'])
    def maintenance(self, request, pk=None):
        if request.method == 'GET':
            if not is_support_staff(request.user):
                return err('You do not have permission to view maintenance records.', 403)
            asset = self.get_object()
            return Response(AssetMaintenanceSerializer(asset.maintenance_records.select_related('technician'), many=True).data)

        serializer = AssetMaintenanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            asset = self._locked(pk)
            if asset.status == A.RETIRED:
                return err('A retired asset cannot be serviced.', 409)
            opening = serializer.validated_data.get('result') == AssetMaintenance.Status.OPEN
            if opening and asset.status == A.ASSIGNED:
                return err('Return the asset from the employee before starting maintenance.', 409)
            record = serializer.save(asset=asset, technician=request.user)
            if opening:
                asset.status = A.MAINTENANCE
                asset.save()
            AssetHistory.objects.create(asset=asset, actor=request.user, action='Maintenance recorded', details=f'{record.maintenance_type}: {record.description} (status: {record.result}).')
        return Response(AssetMaintenanceSerializer(record).data, status=201)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['post'], url_path='complete-maintenance')
    def complete_maintenance(self, request, pk=None):
        with transaction.atomic():
            asset = self._locked(pk)
            if asset.status != A.MAINTENANCE:
                return err('This asset is not under maintenance.', 409)
            open_records = asset.maintenance_records.filter(result=AssetMaintenance.Status.OPEN)
            open_records.update(result=AssetMaintenance.Status.COMPLETED)
            asset.status = A.AVAILABLE
            asset.save()
            AssetHistory.objects.create(asset=asset, actor=request.user, action='Maintenance completed', details='Open maintenance records marked completed; asset returned to Available.')
        return self._ok(asset)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        asset = self.get_object()
        rows = asset.history.select_related('actor').all()
        return Response(AssetHistorySerializer(rows, many=True).data)

    def _change_condition(self, request, pk, new_status, action_label, allowed_from):
        with transaction.atomic():
            asset = self._locked(pk)
            if asset.status not in allowed_from:
                return err(f'Cannot change asset from {asset.get_status_display()} to {dict(A.choices).get(new_status, new_status)}.', 409)
            asset.status = new_status
            asset.save()
            AssetHistory.objects.create(asset=asset, actor=request.user, action=action_label,
                                        details=f'Status changed to {asset.get_status_display()}.')
        return self._ok(asset)

    @action(detail=True, methods=['post'], url_path='mark-damaged')
    def mark_damaged(self, request, pk=None):
        return self._change_condition(request, pk, A.DAMAGED, 'Asset marked damaged', [A.AVAILABLE])

    @action(detail=True, methods=['post'], url_path='mark-lost')
    def mark_lost(self, request, pk=None):
        return self._change_condition(request, pk, A.LOST, 'Asset marked lost', [A.AVAILABLE])

    @action(detail=True, methods=['post'])
    def recover(self, request, pk=None):
        return self._change_condition(request, pk, A.AVAILABLE, 'Asset recovered', [A.LOST, A.DAMAGED])

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        asset = self.get_object()
        return Response(AssetAssignmentSerializer(asset.assignments.select_related('employee', 'assigned_by'), many=True).data)
