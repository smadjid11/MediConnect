from django.contrib import admin
from .models import *

admin.site.register(Speciality)
admin.site.register(AdminProfile)
admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)
admin.site.register(Review)