from django.contrib.auth.forms import PasswordChangeForm, AdminPasswordChangeForm
from django.http import HttpRequest
from django.shortcuts import render, redirect, get_object_or_404, render_to_response
from django.contrib.auth import authenticate, login, get_user_model, logout, update_session_auth_hash
from django.views.generic import View, CreateView, UpdateView, DeleteView
# from social_django.models import UserSocialAuth

from .forms import UserForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.template import RequestContext
from .models import Task
from .forms import TaskForm, LoginForm
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Q

import datetime


@login_required()
def index(request):
    context = {
        'nbar': 'startpage'
    }
    return render(request, 'todolist/startpage.html', context)


@login_required(login_url='todolist:login')
def archive(request):
    all_tasks = Task.objects.filter(user = request.user)
    task_count = Task.objects.filter(archived=True).filter(user = request.user).count()

    # Search function for archive
    queryset_list = Task.objects.archived()
    query = request.GET.get("q")
    if query:
        print("ASJDHJKASHD")
        all_tasks = queryset_list.filter(
            Q(task_text__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

    context = {
        'nbar': 'archive',
        'all_tasks': all_tasks,
        'task_count': task_count,
        'title': 'Archive',
    }
    return render(request, 'todolist/archive.html', context)

@login_required(login_url='todolist:login')
def avatar_screen(request):
    today = datetime.date.today()
    overdue_tasks = Task.objects.filter(user=request.user).filter(due_date__lte=today)
    close_tasks_all = Task.objects.filter(user=request.user).exclude(due_date__lte=today).order_by('due_date')

    close_tasks = []
    i = 0
    for task in close_tasks_all:
        if i < 3:
            close_tasks.append(task)
        i += 1

    context = {
        'overdue_tasks': overdue_tasks,
        'close_tasks': close_tasks,
    }
    return render(request, 'todolist/avatar_screen.html', context)


@login_required(login_url='todolist:login')
def todo(request):
    all_tasks = Task.objects.filter(user=request.user)
    task_count = Task.objects.filter(archived=False).filter(user = request.user).count()

    # Search function for active TODOs
    queryset_list = Task.objects.active()
    query = request.GET.get("q")
    if query:
        all_tasks = queryset_list.filter(
            Q(task_text__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return HttpResponseRedirect(reverse('todolist:todo'))
        else:
            messages.error(request, message="error")
    else:
        form = TaskForm()

    context = {
        'all_tasks': all_tasks,
        'task_count': task_count,
        'form': form,
        'nbar': 'home',
        'title': 'TODOs',
        'queryset_list': queryset_list
    }

    return render(request, 'todolist/index.html', context)


@login_required(login_url='todolist:login')
def todo_detail(request, id=None):
    instance = get_object_or_404(Task, id=id)
    context = {
        "title": 'Detail',
        "instance": instance,
    }
    return render(request, "todolist/todo_detail.html", context)


# Made a separate method for updating todos, seems to work, just need to implement it with modals somehow..
@login_required(login_url='todolist:login')
def todo_update(request, id=None):
    instance = get_object_or_404(Task, id=id)
    form = TaskForm(request.POST or None, instance=instance)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        return HttpResponseRedirect(reverse("todolist:todo"))

    context = {
        "task_text": instance.task_text,
        "task_description": instance.description,
        "due_date": instance.due_date,
        "instance": instance,
        "form": form,
    }
    return render(request, "todolist/edit_task.html", context)


class TaskCreate(CreateView):
    model = Task
    fields = ['task_text', 'description']


class TaskUpdate(UpdateView):
    model = Task
    fields = ['task_text', 'description']


class TaskDelete(DeleteView):
    model = Task
    success_url = reverse_lazy('todolist:todo')


def task_checked(request, pk):
    task = Task.objects.get(pk=pk)
    referer = request.META.get('HTTP_REFERER')
    if ("/archive/" in referer):
        task.archived = False
        task.save()
        return HttpResponseRedirect(reverse("todolist:archive"))
    else:
        task.archived = True
        task.save()
        return HttpResponseRedirect(reverse("todolist:todo"))


class UserFormView(View):
    form_class = UserForm  # blueprint til det vi skal bruke

    template_name = 'todolist/registration_form.html'

    # display blank form
    def get(self, request):  # innebygd funksjon for get-requests. f.eks. laste inn skjema som skal fylles ut
        form = self.form_class(None)
        return render(request, self.template_name, {'form': form})

    # legge til brukeren i databasen
    def post(self, request):  # innebygd funksjon for post-requests
        form = self.form_class(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # cleaned normalized data
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            user.set_password(password)
            user.save()  # lagrer brukeren i databasen

            # Returns User object if credentials are correct
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_active:  # dersom de ikke er banned/utestengt etc

                    login(request, user)

                    return redirect(
                        'todolist:todo')  # maa ogsaa lages! Sender brukeren til startsiden etter registrering?(login)

        return render(request, self.template_name, {'form': form})  # gir skjemaet paa nytt om noe gikk galt


@login_required
def settings(request):
    user = request.user

    try:
        facebook_login = user.social_auth.get(provider='facebook')
    except UserSocialAuth.DoesNotExist:
        facebook_login = None

    can_disconnect = (user.social_auth.count() > 1 or user.has_usable_password())

    return render(request, 'registration/settings.html', {
        'facebook_login': facebook_login,
        'can_disconnect': can_disconnect
    })

@login_required
def password(request):
    if request.user.has_usable_password():
        PasswordForm = PasswordChangeForm
    else:
        PasswordForm = AdminPasswordChangeForm

    if request.method == 'POST':
        form = PasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordForm(request.user)
    return render(request, 'registration/password.html', {'form': form})