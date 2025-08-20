from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *
from datetime import date, timedelta

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email', 'password1', 'password2')

class EditUserForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email')

class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = AdminProfile
        fields = ('gender', 'avatar')

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ('phone', 'birth_date', 'gender', 'avatar', 'agree_terms')
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        today = date.today()
        age_in_days = (today - birth_date).days

        if birth_date > today:
            raise forms.ValidationError("لا يمكن أن يكون تاريخ الميلاد في المستقبل.")
        if age_in_days < 5 * 365:
            raise forms.ValidationError("يجب أن يكون عمرك أكبر من 5 سنوات.")
        return birth_date

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ('speciality', 'bio', 'years_of_experience', 'is_available', 'avatar')

class AddDoctorProfileForm(forms.ModelForm):
    avatar = forms.ImageField(required=True)
    
    class Meta:
        model = DoctorProfile
        fields = ('speciality', 'bio', 'years_of_experience', 'is_available', 'avatar')

class AddAdminProfileForm(forms.ModelForm):
    avatar = forms.ImageField(required=True)
    
    class Meta:
        model = AdminProfile
        fields = ('gender', 'avatar')

class UserLoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'password')

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('patient', 'rating', 'comment')