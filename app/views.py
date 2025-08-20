from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import localdate, localtime
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import Http404
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth import views as auth_views
from chat.models import ChatRoom
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def home(request):
    context = {
        'doctors' : DoctorProfile.objects.all()[:2],
        'reviews' : Review.objects.all().order_by('-rating'),
    }
    return render(request, 'app/pages/home.html', context)

def login_page(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user_login_form = AuthenticationForm(request, data={
            'username' : username,
            'password' : password,
        })
        if user_login_form.is_valid():
            user = user_login_form.get_user()
            login(request, user)
            messages.success(request, 'login successfully !')
            return redirect('home')
        else:
            messages.error(request, 'login error !')
            return redirect('login')
    
    context = {
        
    }
    return render(request, 'app/pages/login.html', context)

def sign_up(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        print(request.POST.get("birth_date"))
        
        sign_up_form = SignUpForm({
            'first_name' : request.POST.get('full_name'),
            'username' : request.POST.get('username'),
            'email' : request.POST.get('email'),
            'password1' : request.POST.get('password1'),
            'password2' : request.POST.get('password2'),
        })

        patient_profile_form = PatientProfileForm(data={
            'phone' : request.POST.get('phone'),
            'birth_date' : request.POST.get('birth_date'),
            'gender' : request.POST.get('gender'),
            'agree_terms' : True,
        },files={
            'avatar' : request.FILES.get('avatar'),
        })
        if sign_up_form.is_valid() and patient_profile_form.is_valid():
            new_user = sign_up_form.save()
            new_profile = patient_profile_form.save(commit=False)
            new_profile.user = new_user
            new_profile.save()
            messages.success(request, "account created successfully")
            return redirect('login')
        else:
            messages.error(request, "there's problem in form")
            return redirect('sign-up')

    context = {

    }
    return render(request, 'app/pages/signup.html', context)

@login_required
def my_profile(request):
    if hasattr(request.user, 'doctorprofile'):
        return redirect('doctor-profile', request.user.username)
    if hasattr(request.user, 'adminprofile'):
        return redirect('admin-profile', request.user.username)
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        # For Edit Profile
        if form_type == 'edit_profile':
            old_avatar = None
            if request.user.patientprofile.avatar:
                old_avatar = request.user.patientprofile.avatar.path
            uploaded_avatar = request.FILES.get('avatar')

            profile_data = {
                'phone' : request.POST.get('phone'),
                'birth_date' : request.POST.get('birth_date'),
                'gender' : request.POST.get('gender'),
            }

            edit_user_form = EditUserForm({
                'first_name' : request.POST.get('full_name'),
                'username' : request.POST.get('username'),
                'email' : request.POST.get('email'),
            }, instance=request.user)

            edit_patient_profile_form = PatientProfileForm(
                data=profile_data,
                files={'avatar': uploaded_avatar},
                instance=request.user.patientprofile
            )

            if edit_user_form.is_valid() and edit_patient_profile_form.is_valid():
                if uploaded_avatar is not None and old_avatar is not None:
                    os.remove(old_avatar)

                edit_user_form.save()
                edit_patient_profile_form.save()

                messages.success(request, "profile edited successfully")
                return redirect('my-profile')
            else:
                messages.error(request, "there's problem in form")
                return redirect('my-profile')
        # For Change Password
        elif form_type == 'edit_password':
            change_password_form = PasswordChangeForm(user=request.user, data={
                'old_password' : request.POST.get('old_password'),
                'new_password1' : request.POST.get('new_password1'),
                'new_password2' : request.POST.get('new_password2'),
            })
            if change_password_form.is_valid():
                user = change_password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('my-profile')
            else:
                messages.error(request, "There's problem in form !")
                return redirect('my-profile')

    context = {
        'profile' : request.user.patientprofile,
    }
    return render(request, 'app/pages/my-profile.html', context)

def doctor_profile(request, username):
    doctor_user = get_object_or_404(User, username=username)
    doctor_profile = get_object_or_404(DoctorProfile, user=doctor_user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'edit_profile':
            # For Edit Profile
            if not hasattr(request.user, 'doctorprofile'):
                raise Http404()
            
            old_avatar = request.user.doctorprofile.avatar.path
            uploaded_avatar = request.FILES.get('avatar')

            profile_data = {
                'speciality' : get_object_or_404(Speciality, name = request.POST.get('speciality')),
                'bio' : request.POST.get('bio'),
                'years_of_experience' : request.POST.get('years_of_experience'),
                'is_available' : True if request.POST.get('is_available') == 'true' else False,
            }
            print(profile_data)

            edit_user_form = EditUserForm({
                'first_name' : request.POST.get('full_name'),
                'username' : request.POST.get('username'),
                'email' : request.POST.get('email'),
            }, instance=request.user)

            edit_doctor_profile_form = DoctorProfileForm(
                data=profile_data,
                files={'avatar': uploaded_avatar},
                instance=request.user.doctorprofile
            )

            print(edit_user_form.errors)
            print(edit_doctor_profile_form.errors)

            if edit_user_form.is_valid() and edit_doctor_profile_form.is_valid():
                if uploaded_avatar is not None and os.path.isfile(old_avatar):
                    os.remove(old_avatar)

                edit_user_form.save()
                edit_doctor_profile_form.save()

                messages.success(request, "profile edited successfully")
                return redirect('my-profile')
            else:
                messages.error(request, "there's problem in form")
                return redirect('my-profile')

        # For Change Password
        elif form_type == 'edit_password':
            if not hasattr(request.user, 'doctorprofile'):
                raise Http404()

            change_password_form = PasswordChangeForm(user=request.user, data={
                'old_password' : request.POST.get('old_password'),
                'new_password1' : request.POST.get('new_password1'),
                'new_password2' : request.POST.get('new_password2'),
            })

            print(change_password_form.errors)

            if change_password_form.is_valid():
                user = change_password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('my-profile')
            else:
                messages.error(request, "There's problem in form !")
                return redirect('my-profile')

    context = {
        'doctor_profile' : doctor_profile,
        'doctor_user' : doctor_user,
        'specialities' : Speciality.objects.all(),
    }
    return render(request, 'app/pages/doctor-profile.html', context)

def admin_profile(request, username):
    admin_user = get_object_or_404(User, username = username)
    admin_profile = admin_user.adminprofile
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'edit_profile':
            # For Edit Profile
            if not hasattr(request.user, 'adminprofile'):
                raise Http404()
            
            old_avatar = request.user.adminprofile.avatar.path
            uploaded_avatar = request.FILES.get('avatar')

            profile_data = {
                'gender' : request.POST.get('gender'),
            }
            print(profile_data)

            edit_user_form = EditUserForm({
                'first_name' : request.POST.get('full_name'),
                'username' : request.POST.get('username'),
                'email' : request.POST.get('email'),
            }, instance=request.user)

            edit_admin_profile_form = AdminProfileForm(
                data=profile_data,
                files={'avatar': uploaded_avatar},
                instance=request.user.adminprofile
            )

            if edit_user_form.is_valid() and edit_admin_profile_form.is_valid():
                if uploaded_avatar is not None and os.path.isfile(old_avatar):
                    os.remove(old_avatar)

                edit_user_form.save()
                edit_admin_profile_form.save()

                messages.success(request, "profile edited successfully")
                return redirect('my-profile')
            else:
                messages.error(request, "there's problem in form")
                return redirect('my-profile')

        # For Change Password
        elif form_type == 'edit_password':
            if not hasattr(request.user, 'adminprofile'):
                raise Http404()

            change_password_form = PasswordChangeForm(user=request.user, data={
                'old_password' : request.POST.get('old_password'),
                'new_password1' : request.POST.get('new_password1'),
                'new_password2' : request.POST.get('new_password2'),
            })

            if change_password_form.is_valid():
                user = change_password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('my-profile')
            else:
                messages.error(request, "There's problem in form !")
                return redirect('my-profile')
    
    context = {
        'admin_user' : admin_user,
        'admin_profile' : admin_profile,
    }
    return render(request, 'app/pages/admin-profile.html', context)

@login_required
def submit_review(request):
    if request.method == 'POST':
        if not hasattr(request.user, 'patientprofile'):
            return JsonResponse({'status' : 'Your Are Not Patient !'})
        
        # For Submit Review
        submit_form = ReviewForm({
            'patient' : get_object_or_404(PatientProfile, user = request.user),
            'rating' : request.POST.get('rating'),
            'comment' : request.POST.get('comment'),
        })
        if submit_form.is_valid():
            submit_form.save()
            messages.success(request, 'review posted successfully')
        else:
            messages.error(request, 'problem in your review form !')
        return redirect(request.POST.get('path', 'home'))
    else:
        raise Http404()

def reviews_page(request):
    reviews = Review.objects.all().order_by('-rating')
    
    if request.method == 'POST':
        if request.POST.get('vote') is not None:
            # For Check
            if request.user.is_anonymous:
                return JsonResponse({'status' : 'your are not patient !', 'status2' : 'login transfer page'})

            if not hasattr(request.user, 'patientprofile'):
                return JsonResponse({'status' : 'your are not patient !', 'status2' : 'show doctor alert'})
            
            # For Helpful Review
            patient_profile = request.user.patientprofile
            vote_value = request.POST.get('vote')
            try:
                review_selected = Review.objects.get(id = request.POST.get('review_id'))
            except Review.DoesNotExist:
                return JsonResponse({'stauts' : 'review does not Exist !'})

            if vote_value == 'agree':
                if patient_profile in review_selected.helpful.all():
                    review_selected.helpful.remove(request.user.patientprofile)
                    return JsonResponse({'status' : 'helpful review removed successfully !', 'status2' : 'done'})
                else:
                    if patient_profile in review_selected.not_helpful.all():
                        review_selected.not_helpful.remove(patient_profile)
                    review_selected.helpful.add(request.user.patientprofile)
                    return JsonResponse({'status' : 'helpful review added successfully !', 'status2' : 'done'})
            # For Not Helpful Review
            elif vote_value == 'disagree':
                if patient_profile in review_selected.not_helpful.all():
                    review_selected.not_helpful.remove(request.user.patientprofile)
                    return JsonResponse({'status' : 'not helpful review removed successfully !', 'status2' : 'done'})
                else:
                    if patient_profile in review_selected.helpful.all():
                        review_selected.helpful.remove(patient_profile)
                    review_selected.not_helpful.add(request.user.patientprofile)
                    return JsonResponse({'status' : 'not helpful review added successfully !', 'status2' : 'done'})
    
    elif request.method == "GET" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        showed_reviews_number = int(request.GET.get('showed_reviews_number'))
        
        reviews_returned = reviews[showed_reviews_number:showed_reviews_number+3]
        if hasattr(request.user, 'patientprofile'):
            data = [
                {
                    'profile_name' : review.patient.user.first_name,
                    'pfp_profile' : review.patient.avatar.url,
                    'id': review.id,
                    'comment': review.comment,
                    'rating': review.rating,
                    'helpful': list(review.helpful.values_list('user__username', flat=True)),
                    'not_helpful': list(review.not_helpful.values_list('user__username', flat=True)),
                    'profile_voted_helpful' : review.helpful.filter(id = request.user.patientprofile.id).exists(),
                    'profile_voted_not_helpful' : review.not_helpful.filter(id = request.user.patientprofile.id).exists(),
                }
                for review in reviews_returned
            ]
            more_reviews = reviews[showed_reviews_number + 3:showed_reviews_number + 4].exists()
            return JsonResponse({"review_objects" : data, 'more_reviews' : more_reviews})
        else:
            data = [
                {
                    'profile_name' : review.patient.user.first_name,
                    'pfp_profile' : review.patient.avatar.url,
                    'id': review.id,
                    'comment': review.comment,
                    'rating': review.rating,
                    'helpful': list(review.helpful.values_list('user__username', flat=True)),
                    'not_helpful': list(review.not_helpful.values_list('user__username', flat=True)),
                }
                for review in reviews_returned
            ]
            # more_reviews = Review.objects.filter(id = last_review_id + 5).exists()
            more_reviews = reviews[showed_reviews_number + 3 : showed_reviews_number + 4].exists()
            return JsonResponse({"review_objects" : data, 'more_reviews' : more_reviews})
    
    reviews = Review.objects.all().order_by('-rating')
    average_rating = 0
    satisfaction_rate = 0
    if reviews.count() > 0:
        for review in reviews:
            # For Average
            average_rating += review.rating
            # For Satisfaction Satisfaction Rate
            if review.rating >= 3:
                satisfaction_rate += 1
        
        average_rating = round(average_rating / reviews.count(), 2)
        satisfaction_rate = round( satisfaction_rate * 100 / reviews.count() , 2)
    
    context = {
        'reviews' : reviews,
        'average_rating' : average_rating,
        'satisfaction_rate' : satisfaction_rate,
    }
    return render(request, 'app/pages/reviews.html', context)
    
def doctors(request):
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        type = request.GET.get('type')
        print(f'type : {type}')
        
        # For Search Suggestion
        if type == 'search':
            query = request.GET.get('query', '')
            print(query)

            results = DoctorProfile.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(speciality__name__icontains=query)
            )[:4]

            data = []
            for doctor in results:
                data.append({
                    'username': doctor.user.username,
                    'full_name': doctor.user.get_full_name(),
                    'speciality': doctor.speciality.name if doctor.speciality else '',
                    'avatar': doctor.avatar.url if doctor.avatar else '',
                })
            
            return JsonResponse({
                'status' : 'success',
                'data' : data,
            })

        # For Load More Doctors
        elif type == 'load_more':
            last_doctor_id = int(request.GET.get("last_doctor_id"))
            print(f'last_doctor_id : {last_doctor_id}')
            try:
                last_doctor = DoctorProfile.objects.get(id=last_doctor_id)
            except DoctorProfile.DoesNotExist:
                return JsonResponse({'status' : 'Last Doctor Does Not Exist !'})
            
            doctors_returned = DoctorProfile.objects.filter(id__range=(last_doctor_id+1, last_doctor_id+1))
            data = [
                {
                    'id': doctor.id,
                    'username' : doctor.user.username,
                    'pfp_profile' : doctor.avatar.url,
                    'full_name' : doctor.user.first_name,
                    'speciality' : doctor.speciality.name,
                    'years_of_experience' : doctor.years_of_experience,
                    
                }
                for doctor in doctors_returned
            ]

            still_more = True if DoctorProfile.objects.filter(id=last_doctor_id+2).exists() else False
            return JsonResponse({
                'status' : 'success',
                'doctors' : data,
                'still_more' : still_more,
            })

    doctors = DoctorProfile.objects.all()
    context = {
        'doctors' : doctors,
    }
    return render(request, 'app/pages/doctors.html', context)

def logout_page(request):
    logout(request)
    return redirect('home')

@login_required
def control(request):
    if not hasattr(request.user, 'adminprofile'):
        raise Http404()
    
    registred_doctors = DoctorProfile.objects.count()
    registered_patients = PatientProfile.objects.count()
    total_reviews = Review.objects.count()
    admin_users = AdminProfile.objects.count()
    context = {
        'registred_doctors' : registred_doctors,
        'registered_patients' : registered_patients,
        'total_reviews' : total_reviews,
        'admin_users' : admin_users,
    }
    return render(request, 'app/pages/controls.html', context)

@login_required
def manage_doctors(request):
    if not hasattr(request.user, 'adminprofile'):
        raise Http404()
    
    # For POST methods
    if request.method == 'POST':
        if not hasattr(request.user, 'adminprofile'):
            raise Http404()
        
        type = request.POST.get('type')

        if type == 'edit':
            # For Edit Doctor Informations
            doctor_user_id = request.POST.get('doctor_id')
            doctor_user = get_object_or_404(User, id=doctor_user_id)
            
            uploaded_avatar = request.FILES.get('avatar')
            old_avatar = doctor_user.doctorprofile.avatar.path
            
            years_of_experience = request.POST.get('years_of_experience')
            bio = request.POST.get('bio')
            is_available = request.POST.get('is_available')
            speciality = get_object_or_404(Speciality, name = request.POST.get('speciality'))

            edit_profile_form = DoctorProfileForm(data = {
                'speciality' : speciality,
                'bio' : bio,
                'years_of_experience' : years_of_experience,
                'is_available' : is_available,
            }, files={'avatar' : uploaded_avatar}, instance=doctor_user.doctorprofile)

            edit_user_form = EditUserForm({
                'first_name' : request.POST.get('full_name'),
                'username' : request.POST.get('username'),
                'email' : request.POST.get('email'),
            }, instance=doctor_user)

            if edit_user_form.is_valid() and edit_profile_form.is_valid():
                if uploaded_avatar is not None and os.path.isfile(old_avatar):
                    os.remove(old_avatar)

                edit_user_form.save()
                edit_profile_form.save()

                messages.success(request, "profile edited successfully")
                return redirect('manage-doctors')
            else:
                messages.error(request, "there's problem in form")
                return redirect('manage-doctors')

        elif type == 'add':
            # For Add Doctor
            uploaded_avatar = request.FILES.get('avatar')
            
            years_of_experience = request.POST.get('years_of_experience')
            bio = request.POST.get('bio')
            is_available = request.POST.get('is_available')
            speciality = get_object_or_404(Speciality, name = request.POST.get('speciality'))

            new_profile_form = AddDoctorProfileForm(data = {
                'speciality' : speciality,
                'bio' : bio,
                'years_of_experience' : years_of_experience,
                'is_available' : is_available,
            }, files={'avatar' : uploaded_avatar})

            sign_up_form = SignUpForm({
                'first_name' : request.POST.get('full_name'),
                'username' : request.POST.get('username'),
                'email' : request.POST.get('email'),
                'password1' : request.POST.get('password1'),
                'password2' : request.POST.get('password2'),
            })

            if sign_up_form.is_valid() and new_profile_form.is_valid():
                new_user = sign_up_form.save()
                new_doctor_profile = new_profile_form.save(commit=False)
                new_doctor_profile.user = new_user
                new_doctor_profile.save()

                messages.success(request, "profile added successfully")
                return redirect('manage-doctors')
            else:
                messages.error(request, "there's problem in form")
                return redirect('manage-doctors')

        elif type == 'delete':
            doctor_user = get_object_or_404(User, id=request.POST.get('doctor_user_id'))
            if hasattr(doctor_user, 'doctorprofile'):
                doctor_profile = doctor_user.doctorprofile
                # For Kill User Websocket Connections
                group_name = f'user_{doctor_user.id}'
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type' : 'force.disconnect'
                    }
                )
                # For Delete User
                os.remove(doctor_profile.avatar.path)
                doctor_user.delete()
                messages.success(request, "doctor deleted successfully")
                return redirect('manage-doctors')
            else:
                messages.error(request, "this profile is not doctor")
                return redirect('manage-doctors')

    doctors = DoctorProfile.objects.all()
    specialities = Speciality.objects.all()
    context = {
        'doctors' : doctors,
        'specialities' : specialities,
    }
    return render(request, 'app/pages/manage-doctors.html', context)

@login_required
def manage_patients(request):
    if not hasattr(request.user, 'adminprofile'):
        raise Http404()
    
    # For Post Method
    if request.method == 'POST':
        if not hasattr(request.user, 'adminprofile'):
            raise Http404()
        
        patient_user = get_object_or_404(User, id = request.POST.get('patient_user_id'))
        if hasattr(patient_user, 'patientprofile'):
            if patient_user.patientprofile.avatar:
                os.remove(patient_user.patientprofile.avatar.path)
            # For Kill User Websocket Connections
            chatrooms_patient_user = ChatRoom.objects.filter(members=patient_user)
            chatroom_names = [chatroom.chatroom_name for chatroom in chatrooms_patient_user]
            group_name = f'user_{patient_user.id}'
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type' : 'force.disconnect'
                }
            )
            for chatroom_name in chatroom_names:
                async_to_sync(channel_layer.group_send)(
                    chatroom_name,
                    {
                        'type' : 'force.disconnect'
                    }
                )
            # For Delete User
            patient_user.delete()
            messages.success(request, "patient deleted successfully")
            return redirect('manage-patients')
        else:
            messages.error(request, "this profile is not patient")
            return redirect('manage-patients')
    
    patients = PatientProfile.objects.all()
    context = {
        'patients' : patients,
    }
    return render(request, 'app/pages/manage-patients.html', context)

@login_required
def manage_reviews(request):
    if not hasattr(request.user, 'adminprofile'):
        raise Http404()
    
    # For Post Method
    if request.method == 'POST':
        if not hasattr(request.user, 'adminprofile'):
            raise Http404()
        
        review_deleted = get_object_or_404(Review, id = request.POST.get('review_id'))
        review_deleted.delete()
        messages.success(request, "review deleted successfully")
        return redirect('manage-reviews')

    reviews = Review.objects.all()
    context = {
        'reviews' : reviews,
    }
    return render(request, 'app/pages/manage-reviews.html', context)

@login_required
def manage_admins(request):
    if not hasattr(request.user, 'adminprofile'):
        raise Http404()
    
    # For Post Method
    if request.method == 'POST':
        if not hasattr(request.user, 'adminprofile'):
            raise Http404()
        
        type = request.POST.get('form_type')
        
        if type == 'add':
            sign_up_form = SignUpForm({
                'first_name' : request.POST.get('full_name'),
                'username' : request.POST.get('username'),
                'email' : request.POST.get('email'),
                'password1' : request.POST.get('password1'),
                'password2' : request.POST.get('password2'),
            })

            add_admin_profile_form = AddAdminProfileForm(data={
                'gender' : request.POST.get('gender'),
            }, files={
                'avatar' : request.FILES.get('avatar'),
            })

            if sign_up_form.is_valid() and add_admin_profile_form.is_valid():
                new_user = sign_up_form.save()
                new_admin = add_admin_profile_form.save(commit=False)
                new_admin.user = new_user
                new_admin.save()
                messages.success(request, "Admin added successfully")
                return redirect('manage-admins')
            else:
                messages.error(request, "there's problem in form")
                return redirect('manage-admins')

        elif type == 'delete':
            admin_deleted = get_object_or_404(User, id = request.POST.get('admin_user_id'))
            if hasattr(admin_deleted, 'adminprofile'):
                # For Kill User Websocket Connections
                group_name = f'user_{admin_deleted.id}'
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type' : 'force.disconnect'
                    }
                )
                # For Delete User
                if admin_deleted.adminprofile.avatar:
                    os.remove(admin_deleted.adminprofile.avatar.path)
                if request.user.id == admin_deleted.id:
                    admin_deleted.delete()
                    messages.success(request, "Admin deleted successfully")
                    return redirect('home')
                else:
                    admin_deleted.delete()
                    messages.success(request, "Admin deleted successfully")
                    return redirect('manage-admins')
    
    admins = AdminProfile.objects.all()
    context = {
        'admins' : admins,
    }
    return render(request, 'app/pages/manage-admins.html', context)
    
@login_required
def my_reviews(request):
    if not hasattr(request.user, 'patientprofile'):
        raise Http404()
    
    # For Post Method
    if request.method == 'POST':
        if not hasattr(request.user, 'patientprofile'):
            raise Http404()
        
        review_deleted = get_object_or_404(Review, id = request.POST.get('review_id'))
        if review_deleted.patient == request.user.patientprofile:
            review_deleted.delete()
            messages.success(request, "review deleted successfully")
            return redirect('my-reviews')
        else:
            messages.error(request, "review is not for you !")
            return redirect('my-reviews')
    
    my_reviews = Review.objects.filter(patient = request.user.patientprofile).order_by('-created_at')
    context = {
        'my_reviews' : my_reviews,
    }
    return render(request, 'app/pages/my-reviews.html', context)


# For Reset Password
def password_reset_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        raise Http404()
    return auth_views.PasswordResetView.as_view()(request, *args, **kwargs)

def password_reset_done_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        raise Http404()
    return auth_views.PasswordResetDoneView.as_view()(request, *args, **kwargs)

def password_reset_confirm_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        raise Http404()
    return auth_views.PasswordResetConfirmView.as_view()(request, *args, **kwargs)

def password_reset_complete_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        raise Http404()
    return auth_views.PasswordResetCompleteView.as_view()(request, *args, **kwargs)
