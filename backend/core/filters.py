import django_filters
from .models import Ticket, Asset


class TicketFilter(django_filters.FilterSet):
    unassigned = django_filters.BooleanFilter(method='filter_unassigned')

    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'category', 'department', 'assigned_agent']

    def filter_unassigned(self, queryset, name, value):
        return queryset.filter(assigned_agent__isnull=bool(value))


class AssetFilter(django_filters.FilterSet):
    class Meta:
        model = Asset
        fields = ['status', 'category', 'department', 'assigned_to']
