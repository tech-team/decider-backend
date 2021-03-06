from django.contrib.auth import get_user_model


class EmailAuthBackend(object):
    UserModel = get_user_model()

    def authenticate(self, username=None, email=None, password=None):
        try:
            if email is not None:
                user = self.UserModel.objects.get(email=email)
            else:
                user = self.UserModel.objects.get(email=username)

            if user.check_password(password) and user.is_active:
                return user
        except self.UserModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return self.UserModel.objects.get(pk=user_id)
        except self.UserModel.DoesNotExist:
            return None


class SocialAuthBackend(object):
    UserModel = get_user_model()

    def authenticate(self, social_id=None, social_site=None, password=None):
        try:
            user = self.UserModel.objects.get(social_id=social_id,
                                              social_site=social_site)

            if user.check_password(password) and user.is_active:
                return user
        except self.UserModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return self.UserModel.objects.get(pk=user_id)
        except self.UserModel.DoesNotExist:
            return None