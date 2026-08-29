from django.contrib.auth.views import (
    LoginView,
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, logout
from django.views.generic import CreateView, UpdateView, View
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from base.models import Profile
from base.forms import UserCreationForm, EmailUpdateForm



class SignUpView(CreateView):

    form_class = UserCreationForm
    template_name = "pages/signup.html"
    success_url = "/"

    def form_valid(self, form):
        response = super().form_valid(form)

        # 登録したユーザーを自動ログイン
        login(
            self.request,
            self.object
        )
        return response



class Login(LoginView):

    template_name = "pages/login.html"



class ProfileUpdateView(LoginRequiredMixin, UpdateView):

    model = Profile
    template_name = "pages/profile.html"
    fields = (
        "profile_image",
        "introduction",
    )
    success_url = "/profile/"


    def get_object(self):

        profile, created = Profile.objects.get_or_create(
            user=self.request.user
        )
        return profile


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # ログインユーザー情報を渡す
        context["user_info"] = self.request.user
        return context


    def post(self, request, *args, **kwargs):

        profile = self.get_object()

        # プロフィール画像削除
        if "delete_image" in request.POST:
            if profile.profile_image:
                if profile.profile_image.name != "profile_images/default.png":
                    profile.profile_image.delete(
                        save=False
                    )
            profile.profile_image = "profile_images/default.png"
            profile.save()
            return redirect("profile")


        return super().post(
            request,
            *args,
            **kwargs
        )









# メールアドレス変更

class EmailUpdateView(LoginRequiredMixin, View):


    def get(self, request):

        form = EmailUpdateForm(
            instance=request.user
        )


        return render(
            request,
            "pages/email_change.html",
            {
                "form": form
            }
        )




    def post(self, request):

        form = EmailUpdateForm(
            request.POST,
            instance=request.user
        )


        if form.is_valid():

            form.save()

            return redirect("profile")



        return render(
            request,
            "pages/email_change.html",
            {
                "form": form
            }
        )









# パスワード変更

class PasswordChange(PasswordChangeView):


    template_name = "pages/password_change.html"


    success_url = reverse_lazy(
        "profile"
    )









# パスワードリセット

class PasswordReset(PasswordResetView):


    template_name = "pages/password_reset/password_reset.html"


    email_template_name = "pages/password_reset/password_reset_email.html"


    # メール件名テンプレート

    subject_template_name = "pages/password_reset/password_reset_subject.txt"


    success_url = reverse_lazy(
        "password_reset_done"
    )






class PasswordResetDone(PasswordResetDoneView):


    template_name = "pages/password_reset/password_reset_done.html"








class PasswordResetConfirm(PasswordResetConfirmView):


    template_name = "pages/password_reset/password_reset_confirm.html"


    success_url = reverse_lazy(
        "password_reset_complete"
    )








class PasswordResetComplete(PasswordResetCompleteView):


    template_name = "pages/password_reset/password_reset_complete.html"









class AccountDeleteView(LoginRequiredMixin, View):


    def post(self, request):

        user = request.user



        # プロフィール画像削除

        try:

            profile = user.profile


            if profile.profile_image:


                if profile.profile_image.name != "profile_images/default.png":


                    profile.profile_image.delete(
                        save=False
                    )


        except Profile.DoesNotExist:

            pass




        # ログアウト

        logout(request)





        # ユーザー削除

        user.delete()



        return redirect("home")