from django.contrib.auth.views import LoginView
from django.urls import reverse


class ProfileLoginView(LoginView):

    def get_success_url(self):

        url = reverse(
            'blog:profile',
            args=(self.request.user.get_username(),)
        )

        return url
