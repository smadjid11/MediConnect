from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.login_page, name='login'),
    path('logout', views.logout_page, name='logout'),
    path('sign-up', views.sign_up, name='sign-up'),
    path('my-profile', views.my_profile, name='my-profile'),
    path('doctor=<str:username>', views.doctor_profile, name='doctor-profile'),
    path('admin=<str:username>', views.admin_profile, name='admin-profile'),
    path('submit-review', views.submit_review, name='submit-review'),
    path('reviews', views.reviews_page, name='reviews'),
    path('doctors', views.doctors, name='doctors'),
    path('control', views.control, name='control'),
    path('manage-doctors', views.manage_doctors, name='manage-doctors'),
    path('manage-patients', views.manage_patients, name='manage-patients'),
    path('manage-reviews', views.manage_reviews, name='manage-reviews'),
    path('manage-admins', views.manage_admins, name='manage-admins'),
    path('my-reviews', views.my_reviews, name='my-reviews'),

    # ...

    path('reset-password/', views.password_reset_view, name='password_reset'),
    path('reset-password/done/', views.password_reset_done_view, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),
]