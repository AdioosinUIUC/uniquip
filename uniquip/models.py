from django.db import models

class Student(models.Model):
    NetId = models.CharField(max_length=50, primary_key=True)
    Name = models.CharField(max_length=100)
    Email = models.CharField(max_length=100)
    PhoneNumber = models.CharField(max_length=20)

    def __str__(self):
        return self.Name

    class Meta:
        db_table = 'students'

class Faculty(models.Model):
    FacultyId = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    Email = models.CharField(max_length=100)

    def __str__(self):
        return self.Name

    class Meta:
        db_table = 'faculty'

class Course(models.Model):
    CRN = models.IntegerField(primary_key=True)
    CourseCode = models.CharField(max_length=30)
    CourseName = models.CharField(max_length=255)
    Credits = models.IntegerField()
    Faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)

    def __str__(self):
        return self.CourseName

    class Meta:
        db_table = 'Courses'

class Enrollment(models.Model):
    NetId = models.ForeignKey(Student, on_delete=models.CASCADE)
    CRN = models.ForeignKey(Course, on_delete=models.CASCADE)
    Semester = models.CharField(max_length=10)
    EnrolledAt = models.DateTimeField()

    class Meta:
        unique_together = (('NetId', 'CRN'),)
        db_table = 'Enrollments'

class Lab(models.Model):
    LabId = models.AutoField(primary_key=True)
    LabName = models.CharField(max_length=100)
    LabLocation = models.CharField(max_length=255)
    OpenHours = models.TimeField()
    CloseHours = models.TimeField()

    def __str__(self):
        return self.LabName

    class Meta:
        db_table = 'Labs'

class CourseLab(models.Model):
    CRN = models.ForeignKey(Course, on_delete=models.CASCADE)
    LabId = models.ForeignKey(Lab, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('CRN', 'LabId'),)
        db_table = 'CourseLab'

class Equipment(models.Model):
    EquipmentId = models.AutoField(primary_key=True)
    Lab = models.ForeignKey(Lab, on_delete=models.CASCADE,db_column='LabId')
    EquipmentName = models.CharField(max_length=200)
    Category = models.CharField(max_length=255)
    IsReservable = models.BooleanField()
    ApprovalRequired = models.BooleanField()

    def __str__(self):
        return self.EquipmentName

    class Meta:
        db_table = 'Equipments'

class Reservation(models.Model):
    ReservationId = models.IntegerField(primary_key=True)
    Equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, db_column='EquipmentId')
    NetId = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='NetId')
    StartTime = models.DateTimeField()
    EndTime = models.DateTimeField()
    Status = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.NetId} - {self.Equipment}"

    class Meta:
        db_table = 'Reservations'

