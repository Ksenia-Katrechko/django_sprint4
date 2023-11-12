from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Comment, Post


FORMAT = '%Y-%m-%dT%H:%M'
User = get_user_model()


class PostForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pub_date'].initial = timezone.localtime(
            timezone.now()
        ).strftime(FORMAT)

    class Meta:
        model = Post
        exclude = ['author']
        widgets = {
            'pub_date': forms.DateTimeInput(
                format=FORMAT,
                attrs={'type': 'datetime-local'}
            )
        }


class ProfileForm(forms.ModelForm):

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email'
        )


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)
