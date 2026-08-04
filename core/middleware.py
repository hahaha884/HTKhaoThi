from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.session.get('force_password_change'):
                try:
                    allowed_paths = [reverse('change_password_first_login'), reverse('logout')]
                    if request.path not in allowed_paths and not request.path.startswith('/static/'):
                        return redirect('change_password_first_login')
                except Exception:
                    pass
        return self.get_response(request)
