from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from .models import Photo, PhotoCategory, PhotoTag
from .forms import PhotoUploadForm, PhotoEditForm
from django.db.models import Q


def photo_list(request):
    """Display all public photos and handle optional search queries."""
    q = request.GET.get('q', '').strip()

    # Base queryset: only public photos
    photos_qs = Photo.objects.filter(privacy='public')

    if q:
        # Search by title, description, owner username, category name, or tag name
        photos_qs = photos_qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(owner__username__icontains=q)
            | Q(category__name__icontains=q)
            | Q(tags__name__icontains=q)
        ).distinct()

    photos = photos_qs.order_by('-created_at')

    # Pagination
    paginator = Paginator(photos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories
    categories = PhotoCategory.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': q,
        'search_count': photos.count() if q else None,
    }

    return render(request, 'photos/photo_list.html', context)


@login_required(login_url='accounts:login')
def photo_upload(request):
    """Upload a new photo"""
    if request.method == 'POST':
        form = PhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.owner = request.user
            photo.save()
            form.save_m2m()
            messages.success(request, '照片已成功上傳！')
            return redirect('photos:detail', photo_id=photo.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PhotoUploadForm()
    
    return render(request, 'photos/photo_upload.html', {'form': form})


def photo_detail(request, photo_id):
    """View photo details"""
    photo = get_object_or_404(Photo, pk=photo_id)
    
    # Check privacy settings
    if photo.privacy == 'private' and photo.owner != request.user:
        raise Http404('此照片不公開。')
    elif photo.privacy == 'friends' and photo.owner != request.user:
        # TODO: Implement friend check
        raise Http404('此照片僅限朋友查看。')
    
    # Increment view count
    photo.increment_view_count()
    
    # Get related photos
    related_photos = Photo.objects.filter(
        owner=photo.owner,
        privacy='public'
    ).exclude(id=photo.id)[:4]
    
    context = {
        'photo': photo,
        'related_photos': related_photos,
    }
    
    return render(request, 'photos/photo_detail.html', context)


@login_required(login_url='accounts:login')
def photo_edit(request, photo_id):
    """Edit photo details"""
    photo = get_object_or_404(Photo, pk=photo_id)
    
    # Check ownership
    if photo.owner != request.user:
        messages.error(request, '您沒有權限編輯此照片。')
        return redirect('photos:detail', photo_id=photo.id)
    
    if request.method == 'POST':
        form = PhotoEditForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            form.save()
            messages.success(request, '照片已更新。')
            return redirect('photos:detail', photo_id=photo.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PhotoEditForm(instance=photo)
    
    return render(request, 'photos/photo_edit.html', {'form': form, 'photo': photo})


@login_required(login_url='accounts:login')
def photo_delete(request, photo_id):
    """Delete a photo"""
    photo = get_object_or_404(Photo, pk=photo_id)
    
    # Check ownership
    if photo.owner != request.user:
        messages.error(request, '您沒有權限刪除此照片。')
        return redirect('photos:detail', photo_id=photo.id)
    
    if request.method == 'POST':
        photo.delete()
        messages.success(request, '照片已刪除。')
        return redirect('photos:my_photos')
    
    return render(request, 'photos/photo_delete.html', {'photo': photo})


@login_required(login_url='accounts:login')
def my_photos(request):
    """View user's own photos"""
    photos = request.user.photos.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(photos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'is_owner': True,
    }
    
    return render(request, 'photos/my_photos.html', context)


def category_photos(request, category_id):
    """View photos in a specific category"""
    category = get_object_or_404(PhotoCategory, pk=category_id)
    photos = Photo.objects.filter(
        category=category,
        privacy='public'
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(photos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
    }
    
    return render(request, 'photos/category_photos.html', context)


def tag_photos(request, tag_name):
    """View photos with a specific tag"""
    tag = get_object_or_404(PhotoTag, name=tag_name)
    photos = Photo.objects.filter(
        tags=tag,
        privacy='public'
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(photos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tag': tag,
        'page_obj': page_obj,
    }
    
    return render(request, 'photos/tag_photos.html', context)
