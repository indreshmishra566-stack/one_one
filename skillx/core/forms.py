from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Message


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('skills_have', 'skills_want', 'bio')
        widgets = {
            'skills_have': forms.TextInput(attrs={
                'placeholder': 'e.g. Python, Guitar, Cooking, Photography',
                'class': 'form-input',
            }),
            'skills_want': forms.TextInput(attrs={
                'placeholder': 'e.g. Spanish, Chess, Drawing, Piano',
                'class': 'form-input',
            }),
            'bio': forms.Textarea(attrs={
                'placeholder': 'Tell others a bit about yourself...',
                'class': 'form-input',
                'rows': 3,
            }),
        }
        labels = {
            'skills_have': 'Skills I Can Teach',
            'skills_want': 'Skills I Want to Learn',
            'bio': 'About Me',
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('content',)
        widgets = {
            'content': forms.TextInput(attrs={
                'placeholder': 'Type your message...',
                'class': 'msg-input',
                'autocomplete': 'off',
            }),
        }
        labels = {'content': ''}
