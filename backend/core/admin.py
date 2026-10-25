from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.template.response import TemplateResponse
from django.urls import reverse

from .models import (User, Department, TicketCategory, AssetCategory, Asset, Ticket, TicketComment,
                     TicketHistory, AssetAssignment, AssetMaintenance, AssetHistory, Notification)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Work details', {'fields': ('phone', 'employee_id', 'department', 'role', 'job_title')}),)
    list_display = ('username', 'email', 'role', 'department', 'is_active')
    list_filter = ('role', 'department', 'is_active')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'title', 'status', 'priority', 'created_by', 'assigned_agent', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('ticket_number', 'title')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('asset_tag', 'name', 'category', 'status', 'assigned_to')
    list_filter = ('status', 'category')
    search_fields = ('asset_tag', 'name', 'serial_number')
    # Replace Django's default bulk-delete action with a confirmation workflow.
    actions = ('delete_assets_with_history',)

    def has_delete_permission(self, request, obj=None):
        # Permanent asset cleanup is deliberately restricted to superusers.
        return request.user.is_active and request.user.is_superuser

    @admin.action(
        description='Permanently delete selected assets and their history (superusers only)',
        permissions=['delete'],
    )
    def delete_assets_with_history(self, request, queryset):
        if not request.user.is_active or not request.user.is_superuser:
            self.message_user(
                request,
                'Only an active superuser can permanently delete assets.',
                level=messages.ERROR,
            )
            return None

        selected_ids = [str(pk) for pk in queryset.values_list('pk', flat=True)]
        if request.POST.get('confirm_permanent_delete') == 'yes':
            # Re-fetch the selected rows on confirmation; never trust client-supplied object data.
            selected_assets = list(Asset.objects.filter(pk__in=selected_ids).order_by('pk'))
            blockers = []
            for asset in selected_assets:
                assignment_count = asset.assignments.count()
                maintenance_count = asset.maintenance_records.count()
                if assignment_count or maintenance_count:
                    blockers.append({
                        'asset': asset,
                        'assignments': assignment_count,
                        'maintenance_records': maintenance_count,
                    })

            # Assignment and maintenance records use PROTECT. Stop the entire operation if any
            # selected asset has those records; do not partially delete the selection.
            if blockers:
                context = {
                    **self.admin_site.each_context(request),
                    'opts': self.model._meta,
                    'assets': selected_assets,
                    'blockers': blockers,
                    'title': 'Cannot delete all selected assets',
                    'cancel_url': reverse('admin:core_asset_changelist'),
                    'protected_records_found': True,
                }
                return TemplateResponse(
                    request,
                    'admin/core/asset/delete_assets_with_history_confirmation.html',
                    context,
                )

            with transaction.atomic():
                for asset in selected_assets:
                    # Explicitly remove the append-only history only in this confirmed,
                    # superuser-only cleanup workflow. No model relationship is changed.
                    asset.history.all().delete()
                    asset.delete()

            self.message_user(
                request,
                f'Successfully deleted {len(selected_assets)} asset(s) and their associated history records.',
                level=messages.SUCCESS,
            )
            return None

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'assets': list(queryset.order_by('pk')),
            'selected_ids': selected_ids,
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
            'title': 'Confirm permanent asset deletion',
            'cancel_url': reverse('admin:core_asset_changelist'),
            'protected_records_found': False,
        }
        return TemplateResponse(
            request,
            'admin/core/asset/delete_assets_with_history_confirmation.html',
            context,
        )


@admin.register(AssetHistory)
class AssetHistoryAdmin(admin.ModelAdmin):
    list_display = ('asset', 'action', 'actor', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('asset__asset_tag', 'action', 'details', 'actor__username')
    readonly_fields = ('asset', 'actor', 'action', 'details', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register([Department, TicketCategory, AssetCategory, TicketComment, TicketHistory,
                     AssetAssignment, AssetMaintenance, Notification])
