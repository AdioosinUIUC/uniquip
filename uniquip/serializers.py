from rest_framework import serializers
from .models import Student, Faculty, Course, Enrollment, Lab, CourseLab, Equipment, Reservation
from. import models

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'

class LabSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lab
        fields = '__all__'

class CourseLabSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLab
        fields = '__all__'

class EquipmentSerializer(serializers.ModelSerializer):
    Lab = LabSerializer(read_only=True)
    class Meta:
        model = Equipment
        fields = '__all__'

class ReservationSerializer(serializers.ModelSerializer):
    Equipment = EquipmentSerializer(read_only=True)
    equipment_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=models.Equipment.objects.all(),
        source='Equipment'
    )
    class Meta:
        model = Reservation
        fields = '__all__'
        extra_kwargs = {
            'Equipment': {'read_only': True}
        }

class EquipmentSerializerCustom(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'