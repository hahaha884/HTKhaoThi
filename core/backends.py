from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import GiaoVien

class PhoneNumberBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Username ở đây sẽ là Số điện thoại
            giao_vien = GiaoVien.objects.get(SDT=username)
            if giao_vien.user and giao_vien.user.check_password(password):
                return giao_vien.user
        except GiaoVien.DoesNotExist:
            return None
        return None
