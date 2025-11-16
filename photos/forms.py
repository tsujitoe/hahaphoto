from django import forms
from .models import Photo, PhotoCategory, PhotoTag


class PhotoUploadForm(forms.ModelForm):
    """Form for uploading photos"""
    tags = forms.CharField(
        label='標籤 (逗號分隔)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例如: 風景, 建築, 肖像'
        })
    )

    class Meta:
        model = Photo
        fields = ['title', 'description', 'image', 'category', 'privacy']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '照片標題'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '照片描述'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'privacy': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = PhotoCategory.objects.all()
        self.fields['category'].empty_label = '選擇分類 (可選)'

    def clean_image(self):
        """Validate image file"""
        image = self.cleaned_data.get('image')
        
        if image:
            # Check file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError('檔案大小不能超過 10MB。')
            
            # Check file type
            valid_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in valid_types:
                raise forms.ValidationError('只允許上傳 JPEG、PNG、GIF 或 WebP 格式的圖片。')
        
        return image

    def save(self, commit=True):
        """Save photo and handle tags"""
        instance = super().save(commit)
        
        # Handle tags
        tags_str = self.cleaned_data.get('tags', '')
        if tags_str:
            tag_names = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            for tag_name in tag_names:
                tag, created = PhotoTag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)
        
        return instance


class PhotoEditForm(forms.ModelForm):
    """Form for editing photo details"""
    tags = forms.CharField(
        label='標籤 (逗號分隔)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例如: 風景, 建築, 肖像'
        })
    )

    class Meta:
        model = Photo
        fields = ['title', 'description', 'category', 'privacy']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'privacy': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = PhotoCategory.objects.all()
        self.fields['category'].empty_label = '選擇分類 (可選)'
        
        # Pre-fill tags
        if self.instance.pk:
            tags_str = ', '.join([tag.name for tag in self.instance.tags.all()])
            self.fields['tags'].initial = tags_str

    def save(self, commit=True):
        """Save photo and handle tags"""
        instance = super().save(commit)
        
        # Clear existing tags
        instance.tags.clear()
        
        # Handle tags
        tags_str = self.cleaned_data.get('tags', '')
        if tags_str:
            tag_names = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            for tag_name in tag_names:
                tag, created = PhotoTag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)
        
        return instance
