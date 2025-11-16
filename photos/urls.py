from django.urls import path
from . import views

app_name = 'photos'

urlpatterns = [
    path('', views.photo_list, name='home'),
    path('upload/', views.photo_upload, name='upload'),
    path('<int:photo_id>/', views.photo_detail, name='detail'),
    path('<int:photo_id>/edit/', views.photo_edit, name='edit'),
    path('<int:photo_id>/delete/', views.photo_delete, name='delete'),
    path('my-photos/', views.my_photos, name='my_photos'),
    path('category/<int:category_id>/', views.category_photos, name='category'),
    path('tag/<str:tag_name>/', views.tag_photos, name='tag'),
]
