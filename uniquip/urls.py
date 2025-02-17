"""
URL configuration for uniquip project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# router.register(r'students', views.StudentViewSet)
# router.register(r'faculty', views.FacultyViewSet)
# router.register(r'courses', views.CourseViewSet)
# router.register(r'enrollments', views.EnrollmentViewSet)
# router.register(r'labs', views.LabViewSet)
# router.register(r'courselabs', views.CourseLabViewSet)
router.register(r'equipments', views.EquipmentViewSet)
router.register(r'reservations', views.ReservationViewSet)

# urlpatterns = [
#     path('api/', include(router.urls)),
# ]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/equipment-availability/', views.EquipmentAvailability.as_view(), name='equipment-availability'),
    path('api/reservations/create/', views.CreateReservations.as_view(), name='create'),
    path('api/equipments-list/', views.EquipmentListView.as_view(), name='equipment-list'),
    path('api/equipments/filter-value', views.CourseListView.as_view(), name='course-list'),
    path('api/reservations/delete/<int:reservation_id>/', views.DeleteReservationView.as_view(), name='delete-reservation'),
    path('api/reservations/faculty/<int:faculty_id>/', views.FacultyReservationListView.as_view(), name='faculty-reservations'),
    path('api/reservations/approve/<int:reservation_id>/', views.ApproveReservationView.as_view(), name='approve-reservation'),
    path('api/equipment/update/<int:pk>/', views.EquipmentUpdateView.as_view(), name='update-equipment'),
    path('api/equipments/faculty/<int:faculty_id>/', views.FacultyEquipmentListView.as_view(), name='faculty-equipment-list'),
    path('api/equipment-usage-report/', views.EquipmentUsageReportView.as_view(), name='equipment-usage-report'),
    path('api/equipment/toggle-reservability/<int:equipment_id>/', views.ToggleEquipmentReservability.as_view(),
         name='toggle-equipment-reservability'),
    path('api/courseload/', views.CourseLoadView.as_view(), name='courseload'),
    path('api/', include(router.urls))
]
