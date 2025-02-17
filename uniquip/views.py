from datetime import timedelta, datetime
from sqlite3 import IntegrityError

from django.db.models import Max
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.db import connection
from .models import Student, Faculty, Course, Enrollment, Lab, CourseLab, Equipment, Reservation
from .serializers import (
    StudentSerializer, FacultySerializer, CourseSerializer, EnrollmentSerializer,
    LabSerializer, CourseLabSerializer, EquipmentSerializer, ReservationSerializer,
    EquipmentSerializerCustom
)
from .filters import ReservationFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import now
from uniquip.utils.s3_logger import S3Logger, LogLevel

# class StudentViewSet(viewsets.ModelViewSet):
#     queryset = Student.objects.all()
#     serializer_class = StudentSerializer

# class FacultyViewSet(viewsets.ModelViewSet):
#     queryset = Faculty.objects.all()
#     serializer_class = FacultySerializer

# class CourseViewSet(viewsets.ModelViewSet):
#     queryset = Course.objects.all()
#     serializer_class = CourseSerializer

# class EnrollmentViewSet(viewsets.ModelViewSet):
#     queryset = Enrollment.objects.all()
#     serializer_class = EnrollmentSerializer

# class LabViewSet(viewsets.ModelViewSet):
#     queryset = Lab.objects.all()
#     serializer_class = LabSerializer

# class CourseLabViewSet(viewsets.ModelViewSet):
#     queryset = CourseLab.objects.all()
#     serializer_class = CourseLabSerializer
logger = S3Logger()

class EquipmentPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100
class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    pagination_class = EquipmentPagination

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        equipment = self.get_object()
        serializer = self.get_serializer(equipment)
        return Response(serializer.data)

class ReservationPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all().select_related('Equipment').order_by('-ReservationId')
    serializer_class = ReservationSerializer
    pagination_class = ReservationPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservationFilter


class EquipmentAvailability(APIView):
    def get(self, request):
        equipment_id = request.query_params.get('equipment_id')
        start_time = request.query_params.get('start_time')
        # end_time = request.query_params.get('end_time')
        if 'T' not in start_time:
            start_time = start_time + "T00:00:00"
        date_object = datetime.fromisoformat(start_time)
        start_time = date_object + timedelta(days=-1)
        new_date_object = date_object + timedelta(days=0)
        start_time = start_time.isoformat()
        end_time = new_date_object.isoformat()
        print(start_time, end_time)

        if not all([equipment_id, start_time, end_time]):
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with connection.cursor() as cursor:
                query = """
                WITH RECURSIVE DateIntervals AS (
                    SELECT %s AS IntervalStart
                    UNION ALL
                    SELECT INTERVALStart + INTERVAL 1 DAY
                    FROM DateIntervals
                    WHERE IntervalStart + INTERVAL 1 DAY < %s
                ),
                HourIntervals AS (
                    SELECT 0 AS IntervalStart
                    UNION ALL
                    SELECT IntervalStart + 1
                    FROM HourIntervals
                    WHERE IntervalStart + 1 < 24
                )
                SELECT 
                    L.LabID,
                    L.LabName,
                    L.OpenHours,
                    L.CloseHours,
                    DATE(DI.IntervalStart) AS Day,
                    ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) AS TimeSlot,
                    SEC_TO_TIME(HI.IntervalStart * 3600) AS StartTimeSlot,
                    SEC_TO_TIME((HI.IntervalStart + 1) * 3600) AS EndTimeSlot,
                    E.EquipmentId
                FROM 
                    uniquip.Labs L
                    INNER JOIN uniquip.Equipments E ON L.LabID = E.LabID
                    CROSS JOIN DateIntervals DI
                    CROSS JOIN HourIntervals HI
                LEFT JOIN uniquip.Reservations R ON E.EquipmentID = R.EquipmentID
                    AND ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) >= R.StartTime AND ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) < R.EndTime
                WHERE 
                    R.ReservationID IS NULL
                    AND CAST(ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) AS TIME) >= L.OpenHours 
                    AND CAST(ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) AS TIME) < L.CloseHours
                    AND ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) >= %s 
                    AND ADDTIME(DI.IntervalStart, SEC_TO_TIME(HI.IntervalStart * 3600)) < %s
                    AND E.EquipmentID = %s
                GROUP BY 
                    L.LabID, 
                    L.LabName,
                    L.LabLocation, 
                    Day,
                    TimeSlot,
                    StartTimeSlot,
                    EndTimeSlot,
                    E.EquipmentId 
                ORDER BY 
                    L.LabID, 
                    Day,
                    TimeSlot;
                """
                cursor.execute(query, [start_time, end_time, start_time, end_time, equipment_id])
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                return Response(results)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

def merge_time_slots(day, time_slots):
    if not time_slots:
        return []

    slots = [datetime.strptime(f"{day}T{slot}", "%Y-%m-%dT%H:%M:%S") for slot in sorted(time_slots)]
    merged_slots = []

    start = slots[0]
    end = start + timedelta(hours=1)

    for current in slots[1:]:
        if current == end:
            end = current + timedelta(hours=1)
        else:
            merged_slots.append((start, end))
            start = current
            end = start + timedelta(hours=1)
    merged_slots.append((start, end))

    return merged_slots


class CreateReservations(APIView):
    def post(self, request, *args, **kwargs):
        print(request.data)
        day = request.data.get('Day')
        time_slots = request.data.get('TimeSlots')
        equipment_id = request.data.get('EquipmentId')
        net_id = request.data.get('NetId')

        try:
            equipment = Equipment.objects.get(pk=equipment_id)
            student = Student.objects.get(pk=net_id)
        except Equipment.DoesNotExist:
            return Response({'error': 'Equipment not found'}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        merged_time_slots = merge_time_slots(day, time_slots)
        print(time_slots)
        print(merged_time_slots)

        reservations = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT MAX(ReservationId) FROM reservations")
                last_id = cursor.fetchone()[0]
                new_id = (last_id or 0) + 1

                for start_time, end_time in merged_time_slots:
                    reservationStatus = 'Reserved' if not equipment.ApprovalRequired else 'Approval Required'

                    sql = """
                                INSERT INTO reservations (ReservationId, EquipmentId, NetId, StartTime, EndTime, Status)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                    cursor.execute(sql, [new_id, equipment_id, net_id, start_time, end_time, reservationStatus])
                    reservations.append({
                        'ReservationId': new_id,
                        'EquipmentId': equipment_id,
                        'NetId': net_id,
                        'StartTime': start_time.isoformat(),
                        'EndTime': end_time.isoformat(),
                        'Status': reservationStatus
                    })
                    new_id += 1
                connection.commit()

        except IntegrityError as e:
            connection.rollback()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(reservations, status=status.HTTP_201_CREATED)

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class EquipmentListView(APIView):
    pagination_class = CustomPagination()

    def get(self, request):
        logger.log("Getting Equipment List", LogLevel.INFO)
        page_number = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        net_id = request.query_params.get('net_id')
        course_code = request.query_params.get('course_code', None)
        equipment_name = request.query_params.get('equipment_name', None)
        if equipment_name is not None and equipment_name.strip() == "":
            equipment_name = None
        if equipment_name is not None:
            equipment_name = "%" + equipment_name.strip() + "%"
        if course_code == "All":
            course_code = None

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT E.EquipmentId, E.LabId, E.EquipmentName, E.Category, E.IsReservable, E.ApprovalRequired, L.LabName
                FROM uniquip.Equipments AS E
                JOIN uniquip.CourseLab AS CL ON E.LabId = CL.LabId 
                JOIN uniquip.Enrollments AS C ON C.CRN = CL.CRN
                LEFT JOIN uniquip.Courses Co ON C.CRN = Co.CRN 
                LEFT JOIN uniquip.Labs AS L ON L.LabId = E.LabId
                WHERE ApprovalRequired = 1
                    AND NetId = %s
                    AND IsReservable = 1
                    AND (%s IS NULL OR Co.CourseCode = %s)
                    AND (%s IS NULL OR E.EquipmentName like %s)
                UNION 
                SELECT E.EquipmentId, E.LabId, E.EquipmentName, E.Category, E.IsReservable, E.ApprovalRequired, L.LabName
                FROM uniquip.Equipments AS E
                LEFT JOIN uniquip.Labs AS L ON L.LabId = E.LabId
                WHERE ApprovalRequired = 0
                    AND IsReservable = 1
                    AND (%s IS NULL OR E.EquipmentName like %s)
                LIMIT %s OFFSET %s
            """, [net_id, course_code, course_code, equipment_name, equipment_name, equipment_name, equipment_name, int(page_size), (int(page_number) - 1) * int(page_size)])
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
            cursor.execute("""
                SELECT COUNT(*) FROM (
                    SELECT E.EquipmentId
                    FROM uniquip.Equipments AS E
                    JOIN uniquip.CourseLab AS CL ON E.LabId = CL.LabId 
                    JOIN uniquip.Enrollments AS C ON C.CRN = CL.CRN
                    LEFT JOIN uniquip.Courses Co ON C.CRN = Co.CRN 
                    LEFT JOIN uniquip.Labs AS L ON L.LabId = E.LabId
                    WHERE ApprovalRequired = 1
                        AND NetId = %s
                        AND IsReservable = 1
                        AND (%s IS NULL OR Co.CourseCode = %s)
                        AND (%s IS NULL OR E.EquipmentName like %s)
                    UNION 
                    SELECT E.EquipmentId
                    FROM uniquip.Equipments AS E
                    LEFT JOIN uniquip.Labs AS L ON L.LabId = E.LabId
                    WHERE ApprovalRequired = 0
                        AND IsReservable = 1
                        AND (%s IS NULL OR E.EquipmentName like %s)
                ) AS combined
            """, [net_id, course_code, course_code, equipment_name, equipment_name, equipment_name, equipment_name])
            count = cursor.fetchone()[0]

            finalResult = {}
            finalResult['count'] = count
            finalResult['results'] = results

        return Response(finalResult)
        # return self.pagination_class.get_paginated_response(serializer.data)

class CourseListView(APIView):
    def get(self, request, *args, **kwargs):
        net_id = request.query_params.get('net_id', '')

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT Distinct C.CourseCode
                FROM uniquip.Enrollments E
                LEFT JOIN uniquip.Courses C ON E.CRN = C.CRN
                INNER JOIN uniquip.CourseLab CL ON CL.CRN = C.CRN
                WHERE E.NetId = %s;
            """, [net_id])
            rows = cursor.fetchall()

        results = [row[0] for row in rows]

        return Response(results, status=status.HTTP_200_OK)

class DeleteReservationView(APIView):
    def delete(self, request, reservation_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM reservations WHERE ReservationId = %s", [reservation_id])
                if cursor.rowcount == 0:
                    return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
                connection.commit()
            return Response({'success': 'Reservation deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            connection.rollback()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FacultyReservationListView(APIView):
    def get(self, request, faculty_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT distinct ReservationId, E.EquipmentName, S.Name, R.NetId, R.StartTime, R.EndTime, R.Status
                    FROM (
                        SELECT FacultyId
                        FROM uniquip.Faculty
                        WHERE FacultyId = %s
                    ) AS F
                    JOIN Courses Co ON Co.FacultyId = F.FacultyId
                    JOIN CourseLab CL ON CL.CRN = Co.CRN
                    JOIN Enrollments En ON En.CRN = Co.CRN
                    JOIN Students S ON S.NetId = En.NetId
                    JOIN Labs L ON L.LabId = CL.LabId
                    JOIN Equipments E ON E.LabId = L.LabId
                    JOIN Reservations R ON R.EquipmentId = E.EquipmentId
                    WHERE R.Status = 'Approval Required' AND R.NetId = S.NetId
                """, [faculty_id])
                columns = [col[0] for col in cursor.description]
                reservations = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(reservations, status=status.HTTP_200_OK)


class ApproveReservationView(APIView):
    def patch(self, request, reservation_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE uniquip.Reservations
                    SET Status = 'Reserved'
                    WHERE ReservationId = %s AND Status = 'Approval Required'
                """, [reservation_id])

                if cursor.rowcount == 0:
                    return Response({'error': 'No reservation found requiring approval or already approved'},
                                    status=status.HTTP_404_NOT_FOUND)

                connection.commit()
            return Response({'success': 'Reservation approved'}, status=status.HTTP_200_OK)
        except Exception as e:
            connection.rollback()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EquipmentUpdateView(APIView):
    def patch(self, request, pk):
        approval_required = request.data.get('ApprovalRequired', None)

        if approval_required is None:
            return Response({'error': 'ApprovalRequired field is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with connection.cursor() as cursor:
                sql = "UPDATE uniquip.Equipments SET ApprovalRequired = %s WHERE EquipmentId = %s"

                cursor.execute(sql, [approval_required, pk])

                if cursor.rowcount == 0:
                    return Response({'error': 'Equipment not found or no update needed'},
                                    status=status.HTTP_404_NOT_FOUND)

                connection.commit()
                return Response({'success': 'Equipment updated'}, status=status.HTTP_200_OK)

        except IntegrityError as e:
            connection.rollback()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            connection.rollback()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FacultyEquipmentListView(APIView):
    def get(self, request, faculty_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT E.LabId, E.EquipmentId, E.EquipmentName, E.ApprovalRequired, E.IsReservable
                    FROM (
                        SELECT FacultyId
                        FROM uniquip.Faculty
                        WHERE FacultyId = %s
                    ) AS F
                    JOIN Courses Co ON Co.FacultyId = F.FacultyId
                    JOIN CourseLab CL ON CL.CRN = Co.CRN
                    JOIN Labs L ON L.LabId = CL.LabId
                    JOIN Equipments E ON E.LabId = L.LabId
                """, [faculty_id])
                columns = [col[0] for col in cursor.description]
                equipments = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(equipments, status=status.HTTP_200_OK)

class EquipmentUsageReportView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with connection.cursor() as cursor:
                cursor.callproc('GetEquipmentUsageReport', [start_date, end_date])
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ToggleEquipmentReservability(APIView):
    def patch(self, request, equipment_id):
        current_time = now()
        try:
            with connection.cursor() as cursor:
                cursor.execute("BEGIN;")

                cursor.execute("""
                    UPDATE uniquip.Equipments
                    SET IsReservable = %s
                    WHERE EquipmentId = %s
                """, [False, equipment_id])

                if cursor.rowcount == 0:
                    cursor.execute("ROLLBACK;")
                    return Response({'error': 'Equipment not found or no update needed'}, status=status.HTTP_404_NOT_FOUND)

                cursor.execute("""
                    UPDATE uniquip.Reservations
                    SET Status = 'Cancelled'
                    WHERE EquipmentId = %s AND StartTime > %s
                """, [equipment_id, current_time])

                cursor.execute("COMMIT;")
                return Response({'success': 'Equipment reservability toggled and future reservations cancelled'}, status=status.HTTP_200_OK)

        except Exception as e:
            with connection.cursor() as cursor:
                cursor.execute("ROLLBACK;")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseLoadView(APIView):
    def get(self, request):
        start_threshold = request.query_params.get('start_threshold', '2024-01-15')
        end_threshold = request.query_params.get('end_threshold', '2024-05-10')

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT e.CRN, c.CourseName, 
                        SUM(TIMESTAMPDIFF(HOUR, StartTime, EndTime)) AS TotalHoursBooked 
                    FROM Enrollments e
                    LEFT JOIN Courses c ON c.CRN = e.CRN
                    INNER JOIN CourseLab cl ON cl.CRN = c.CRN
                    LEFT JOIN Reservations r ON r.NetId = e.NetId
                    WHERE StartTime >= %s AND EndTime <= %s
                    GROUP BY e.CRN, c.CourseName 
                    ORDER BY TotalHoursBooked DESC
                """, [start_threshold, end_threshold])

                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)