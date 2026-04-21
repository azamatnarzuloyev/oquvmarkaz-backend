import django_filters
from .models import Lead


class LeadFilter(django_filters.FilterSet):
    status      = django_filters.MultipleChoiceFilter(choices=Lead.status.field.choices)
    source      = django_filters.MultipleChoiceFilter(choices=Lead.source.field.choices)
    assigned_to = django_filters.NumberFilter(field_name='assigned_to__id')
    date_from   = django_filters.DateFilter(field_name='created_at__date', lookup_expr='gte')
    date_to     = django_filters.DateFilter(field_name='created_at__date', lookup_expr='lte')

    class Meta:
        model  = Lead
        fields = ('status', 'source', 'assigned_to', 'date_from', 'date_to')
