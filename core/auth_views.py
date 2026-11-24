from django.contrib.auth.views import LoginView


class ChurchLoginView(LoginView):
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.POST.get("remember"):
            # Shared church computers: end the session when the browser closes.
            self.request.session.set_expiry(0)
        return response
