from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from .models import AddState
from .views import AdminOrHeadOfficeRequiredMixin
from .whatsapp_forms import WhatsAppSupportForm
from .language import normalize_state


class WhatsAppManagementView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = AddState
    template_name = "web/headoffice/whatsapp_management.html"
    context_object_name = "states"

    def get_queryset(self):
        return AddState.objects.order_by("state_name")

    def _states_with_forms(self, submitted_state=None):
        states = list(self.get_queryset())
        for state in states:
            state.whatsapp_form = (
                submitted_state if submitted_state is not None and submitted_state.instance.pk == state.pk
                else WhatsAppSupportForm(instance=state)
            )
            state.is_default_fallback = normalize_state(state.state_name) == "kerala" or normalize_state(state.slug) == "kerala"
        return states

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["states"] = self._states_with_forms()
        return context

    def post(self, request, *args, **kwargs):
        state_id = request.POST.get("state_id")
        if not state_id or not str(state_id).isdigit():
            return HttpResponseBadRequest("A valid state is required.")

        state = get_object_or_404(AddState, pk=state_id)
        form = WhatsAppSupportForm(request.POST, instance=state)
        if form.is_valid():
            form.save()
            messages.success(request, _("WhatsApp support settings saved."))
            return redirect("web:whatsapp_management")

        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context["states"] = self._states_with_forms(submitted_state=form)
        return render(request, self.template_name, context)
