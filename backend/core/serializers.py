from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers

from .models import (Department, TicketCategory, AssetCategory, Asset, AssetHistory, Ticket, TicketComment,
                     TicketHistory, AssetAssignment, AssetMaintenance, Notification)
from .permissions import is_admin, is_support_staff
from . import workflow

User = get_user_model()


def display_name(user):
    """Full name, falling back to username, then email, so the UI never shows a blank."""
    if not user:
        return None
    return user.get_full_name() or user.username or user.email


# ---------------------------------------------------------------- users
class UserSerializer(serializers.ModelSerializer):
    """Admin user management. Never exposes password hashes."""
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    full_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'employee_id',
                  'department', 'department_name', 'role', 'job_title', 'is_active', 'date_joined', 'password']
        read_only_fields = ['id', 'date_joined']

    def get_full_name(self, obj):
        return display_name(obj)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_employee_id(self, value):
        return value or None  # unique + blank string would collide; store NULL instead

    def validate(self, attrs):
        request = self.context.get('request')
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'A password is required for new users.'})
        if self.instance is not None:
            if request and self.instance.pk == request.user.pk:
                # stop an admin from locking themselves out by accident
                if 'role' in attrs and attrs['role'] != self.instance.role:
                    raise serializers.ValidationError({'role': 'You cannot change your own role.'})
                if 'is_active' in attrs and attrs['is_active'] is False:
                    raise serializers.ValidationError({'is_active': 'You cannot deactivate your own account.'})
            current_is_admin = self.instance.role == User.Role.ADMIN or self.instance.is_superuser
            loses_admin = ('is_active' in attrs and attrs['is_active'] is False) or ('role' in attrs and attrs['role'] != User.Role.ADMIN)
            if current_is_admin and loses_admin:
                active_admins = User.objects.filter(is_active=True).filter(
                    Q(role=User.Role.ADMIN) | Q(is_superuser=True)
                ).exclude(pk=self.instance.pk).count()
                if active_admins == 0:
                    raise serializers.ValidationError({'role': 'The last active administrator cannot be deactivated or demoted.'})
        dept = attrs.get('department')
        if dept is not None and not dept.is_active and (self.instance is None or self.instance.department_id != dept.pk):
            raise serializers.ValidationError({'department': 'This department is inactive.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class MeSerializer(serializers.ModelSerializer):
    """The signed-in user's own profile (read-only)."""
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    full_name = serializers.SerializerMethodField()
    role_label = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'department',
                  'department_name', 'role', 'role_label', 'job_title']
        read_only_fields = fields

    def get_full_name(self, obj):
        return display_name(obj)


class UserBriefSerializer(serializers.ModelSerializer):
    """Minimal directory entry for support staff (assignment dropdowns)."""
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'role', 'department_name']

    def get_full_name(self, obj):
        return display_name(obj)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data, role=User.Role.EMPLOYEE)  # role can never come from the client
        user.set_password(password)
        user.save()
        return user


# ---------------------------------------------------------------- lookups
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['created_at']


class TicketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketCategory
        fields = '__all__'


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = '__all__'


# ---------------------------------------------------------------- assets
class AssetSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Asset
        fields = '__all__'
        # status and assigned_to change only through the assign / return / maintenance / retire actions
        read_only_fields = ['status', 'assigned_to', 'created_at', 'updated_at']

    def get_assigned_to_name(self, obj):
        return display_name(obj.assigned_to)

    def validate(self, attrs):
        dept = attrs.get('department')
        if dept is not None and not dept.is_active and (self.instance is None or self.instance.department_id != dept.pk):
            raise serializers.ValidationError({'department': 'This department is inactive.'})
        category = attrs.get('category')
        if category is not None and not category.is_active and (self.instance is None or self.instance.category_id != category.pk):
            raise serializers.ValidationError({'category': 'This asset category is inactive.'})
        purchase, warranty = attrs.get('purchase_date'), attrs.get('warranty_expiry')
        if purchase and warranty and warranty < purchase:
            raise serializers.ValidationError({'warranty_expiry': 'Warranty cannot expire before the purchase date.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not is_support_staff(request.user):
            data.pop('purchase_price', None)  # employees see only what they need
            data.pop('notes', None)
        return data


class AssetHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetHistory
        fields = ['id', 'asset', 'actor', 'actor_name', 'action', 'details', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return display_name(obj.actor)


class AssetAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = AssetAssignment
        fields = ['id', 'asset', 'employee', 'employee_name', 'assigned_by', 'assigned_by_name',
                  'assigned_at', 'returned_at', 'reason', 'is_active']
        read_only_fields = fields

    def get_employee_name(self, obj):
        return display_name(obj.employee)

    def get_assigned_by_name(self, obj):
        return display_name(obj.assigned_by)

    def get_is_active(self, obj):
        return obj.returned_at is None


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetMaintenance
        fields = ['id', 'asset', 'maintenance_type', 'description', 'technician', 'technician_name',
                  'maintenance_date', 'cost', 'result', 'notes', 'created_at']
        read_only_fields = ['id', 'asset', 'technician', 'created_at']

    def get_technician_name(self, obj):
        return display_name(obj.technician)

    def validate_cost(self, value):
        if value < 0:
            raise serializers.ValidationError('Cost cannot be negative.')
        return value


# ---------------------------------------------------------------- tickets
class TicketSerializer(serializers.ModelSerializer):
    """Read representation. Includes what the CURRENT user is allowed to do, so the UI stays honest."""
    created_by_name = serializers.SerializerMethodField()
    assigned_agent_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    asset_tag = serializers.CharField(source='asset.asset_tag', read_only=True, default=None)
    asset_name = serializers.SerializerMethodField()
    allowed_transitions = serializers.SerializerMethodField()
    can_assign = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'  # output only: input goes through TicketWriteSerializer

    def _user(self):
        request = self.context.get('request')
        return request.user if request else None

    def get_created_by_name(self, obj):
        return display_name(obj.created_by)

    def get_assigned_agent_name(self, obj):
        return display_name(obj.assigned_agent)

    def get_asset_name(self, obj):
        return obj.asset.display_name if obj.asset else None

    def get_allowed_transitions(self, obj):
        user = self._user()
        return workflow.allowed_transitions(user, obj) if user else []

    def get_can_assign(self, obj):
        user = self._user()
        return bool(user) and workflow.can_assign(user, obj)

    def get_can_edit(self, obj):
        user = self._user()
        return bool(user) and workflow.can_edit(user, obj)


class TicketWriteSerializer(serializers.ModelSerializer):
    """Input for create / edit. Creator, status, department and agent are never taken from the client."""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'asset']

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError('Title must be at least 5 characters.')
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Please describe the problem in at least 10 characters.')
        return value

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError('This category is no longer available.')
        return value

    def validate_asset(self, asset):
        if asset is None:
            return asset
        user = self.context['request'].user
        if asset.status == Asset.Status.RETIRED:
            raise serializers.ValidationError('A retired asset cannot be linked to a ticket.')
        if not is_support_staff(user) and asset.assigned_to_id != user.id:
            raise serializers.ValidationError('You can only link an asset that is assigned to you.')
        return asset


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.CharField(source='author.role', read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'author', 'author_name', 'author_role', 'comment', 'is_internal', 'created_at']
        read_only_fields = ['id', 'ticket', 'author', 'author_name', 'author_role', 'created_at']

    def get_author_name(self, obj):
        return display_name(obj.author)

    def validate_comment(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Comment cannot be empty.')
        return value


class TicketHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketHistory
        fields = ['id', 'ticket', 'actor', 'actor_name', 'action', 'details', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return display_name(obj.actor)


class NotificationSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True, default=None)
    asset_tag = serializers.CharField(source='asset.asset_tag', read_only=True, default=None)

    class Meta:
        model = Notification
        fields = ['id', 'message', 'ticket', 'ticket_number', 'asset', 'asset_tag', 'is_read', 'created_at']
        read_only_fields = fields
