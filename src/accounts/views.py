# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.urls.base import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import UpdateView, CreateView
from django.core.exceptions import ObjectDoesNotExist

from accounts.forms import UserUpdateForm, UserRegistrationForm
from dataloaderinterface.forms import OrganizationForm


class UserUpdateView(UpdateView):
    form_class = UserUpdateForm
    template_name = 'registration/account.html'
    model = get_user_model()

    def get_object(self, queryset=None):
        return self.request.user

    def get_hydroshare_account(self):
        return self.request.user.hydroshare_account

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)

        try:
            context['hs_account'] = self.request.user.hydroshare_account
        except ObjectDoesNotExist:
            pass

        context['organization_form'] = OrganizationForm()
        return context

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return super(UserUpdateView, self).get(request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):

        if request.POST.get('disconnect-hydroshare-account'):
            request.user.hydroshare_account.delete()
            form = self.get_form_class()(request.POST, instance=request.user)

            context = {
                'form': form,
                'organization_form': OrganizationForm(),
                'hs_accounts': None
            }
            return render(request, self.template_name, context=context)
        else:
            form = self.get_form_class()(request.POST, instance=request.user)

            if form.is_valid():
                form.instance.save(update_fields=form.changed_data)
                messages.success(request, 'Your information has been updated successfully.')
                return HttpResponseRedirect(reverse('user_account'))
            else:
                messages.error(request, 'There were some errors in the form.')
                return render(request, self.template_name, {'form': form, 'organization_form': OrganizationForm()})


class UserRegistrationView(CreateView):
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('home')
    model = get_user_model()

    def get_context_data(self, **kwargs):
        context = super(UserRegistrationView, self).get_context_data(**kwargs)
        context['organization_form'] = OrganizationForm()
        return context

    def post(self, request, *args, **kwargs):
        response = super(UserRegistrationView, self).post(request, *args, **kwargs)
        form = self.get_form()

        if form.instance.id:
            login(request, form.instance)

        return response

def logout_view(request):
     # use django to log user out, and render a custom logout page to fix issue #558
     from django.contrib.auth import logout
     logout(request)
     return render (
        request,
        'registration/logout.html'
    )
