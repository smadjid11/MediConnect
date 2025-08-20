from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MinValueValidator, MaxValueValidator

class Speciality(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to="avatars/admin", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')])

    def __str__(self):
        return f"{self.user.get_full_name()}"

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    speciality = models.ForeignKey(Speciality, on_delete=models.SET_NULL, null=True)
    bio = models.TextField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to="avatars/doctor", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()}"
    
    class Meta:
        ordering = ('-id', )

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')])
    avatar = models.ImageField(upload_to="avatars/patient", blank=True, null=True)
    agree_terms = models.BooleanField(default=False)
    last_online_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name()
    
    class Meta:
        ordering = ('-id',)

class Review(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[ MinValueValidator(1), MaxValueValidator(5) ])
    comment = models.TextField(max_length=500)
    helpful = models.ManyToManyField(PatientProfile, related_name='helpful_reviews', blank=True)
    not_helpful = models.ManyToManyField(PatientProfile, related_name='not_helpful_reviews', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-rating',)

    def __str__(self):
        return f'{self.patient.user.username} : {self.comment}'