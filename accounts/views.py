from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from .forms import UserRegistrationForm, UserProfileForm


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, '註冊成功！請登入。')
            return redirect('accounts:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'歡迎回來，{user.username}！')
            return redirect('photos:home')
        else:
            messages.error(request, '用戶名或密碼不正確。')
    
    return render(request, 'accounts/login.html')


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, '您已成功登出。')
    return redirect('photos:home')


def profile_view(request, user_id):
    """View user profile"""
    user = get_object_or_404(User, pk=user_id)
    profile = user.profile
    photos = user.photos.filter(privacy='public').order_by('-created_at')
    
    context = {
        'user': user,
        'profile': profile,
        'photos': photos,
        'photo_count': user.photos.count(),
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required(login_url='accounts:login')
def profile_edit(request):
    """Edit user profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '個人資料已更新。')
            return redirect('accounts:profile', user_id=request.user.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})
