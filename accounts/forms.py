from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile


class UserRegistrationForm(UserCreationForm):
    """Form for user registration"""
    email = forms.EmailField(
        label='電子郵件',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        label='名字',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label='姓氏',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '用戶名'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': '密碼'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': '確認密碼'})

    def clean_email(self):
        """Check if email is already registered"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('此電子郵件已被註冊。')
        return email


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    
    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar', 'location', 'birth_date', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '關於您的簡介'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '位置'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': '網站'}),
        }
