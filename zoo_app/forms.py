from django import forms
from django.contrib.auth.models import User
from zoo_app.models import UserProfile, Task, Resource

# ======== VARIOUS REGISTRATION/LOGIN FORMS (Abdul) ========

# Registration form - validates that passwords match before saving
class UserRegisterForm(forms.ModelForm):
    # PasswordInput hides the typed characters
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")


# Login form - plain username/password, no model binding
class UserLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())


# Profile form - currently no editable fields; kept for future expansion
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ()


# Task creation form — uses datetime-local input with explicit English locale
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'deadline')
        widgets = {
            # lang='en' prevents the browser from rendering the date picker in the OS language
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'lang': 'en'}),
        }


# Resource/note form - used on the Notes page to attach links or text to a task
class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ('title', 'content', 'url', 'type')
