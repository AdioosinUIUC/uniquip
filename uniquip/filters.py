import django_filters
from .models import Reservation

class ReservationFilter(django_filters.FilterSet):
    start_date = django_filters.DateTimeFilter(field_name="StartTime", lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name="EndTime", lookup_expr='lte')
    equipment_id = django_filters.NumberFilter(field_name="Equipment_id")
    net_id = django_filters.CharFilter(field_name="NetId_id")

    class Meta:
        model = Reservation
        fields = ['start_date', 'end_date', 'equipment_id', 'net_id']
