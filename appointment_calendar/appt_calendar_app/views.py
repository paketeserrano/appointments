from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound
from .forms import AppointmentForm, SignUpForm, BusinessAppearanceForm, AppointmentCancelForm, AddressForm, CreateAccountForm, \
                                    CreateEventForm, SelectWorkerForm, SelectEventForm, InactiveEventForm, SelectDateTimeForm, \
                                    CustomerInformationForm, EventQuestionForm, EventAnswerForm, AppointmentSearchForm
from django.conf import settings
from django.core.mail import send_mail
from .models import Appointment, Event, Account, AccountInvitation, BusinessAppearance, Invitee, CustomUser, OpenningTime, \
                    BusinessEventImageUpload, SpecialDay, WEEKDAYS, EventUI, AccountUI, UserWorkImageUpload, AppointmentCancellation, \
                    EventPageOptions, AppointmentQuestionResponse, EventPageQuestion, Address
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.core import serializers
import json
from formtools.wizard.views import SessionWizardView
from datetime import datetime, timedelta, time
from .libs.send_emails import gmail_send, gmail_compose, gmail_credentials
from django.urls import reverse_lazy, reverse
from django.contrib.sites.shortcuts import get_current_site
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from django.views.generic import View, DetailView
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.files.storage import FileSystemStorage
import os
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth import get_user_model
from .libs import utils
from django.templatetags.static import static
from django.forms.models import model_to_dict
from collections import defaultdict

def user_owns_resource(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        # Assuming 'custom_user_id' is passed as a keyword argument to the view
        custom_user_id = kwargs.get('custom_user_id') or request.GET.get('custom_user_id') or request.POST.get('custom_user_id')
        if request.user.is_authenticated:
            if str(request.user.id) == str(custom_user_id):
                return function(request, *args, **kwargs)
            else:
                return JsonResponse({'error': 'Unauthorized'}, status=403)
        else:
            return JsonResponse({'error': 'Authentication required'}, status=401)

    return wrap

def user_is_event_admin(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

        # Extract event ID from request; adjust as necessary based on how event_id is passed
        event_id = kwargs.get('event_id') or request.GET.get('event_id') or request.POST.get('event_id')
        if not event_id:
            return JsonResponse({'success': False, 'message': 'Event ID missing.'}, status=400)

        event = get_object_or_404(Event, id=event_id)
        
        # Check if the user is an admin of the business associated with the event
        if request.user.customuser in event.account.admins.all():
            return view_func(request, *args, **kwargs)
        else:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    return _wrapped_view

def business_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        business_id = kwargs.get('business_id')
        business = get_object_or_404(Account, pk=business_id)
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login') + '?next=' + request.path)
        
        # Check if the user is an admin of the business
        if not request.user.customuser in business.admins.all():
            raise PermissionDenied("You are not an admin of this event.")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

class EventAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        event_id = kwargs.get('pk')
        event = get_object_or_404(Event, pk=event_id)
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login') + '?next=' + request.path)
        if not request.user.customuser in event.account.admins.all():
            raise PermissionDenied("You are not an admin of this event.")
        return super().dispatch(request, *args, **kwargs)
    
class BusinessAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        business_id = kwargs.get('business_id')
        business = get_object_or_404(Account, pk=business_id)
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login') + '?next=' + request.path)
        if not request.user.customuser in business.admins.all():
            raise PermissionDenied("You are not an admin of this event.")
        return super().dispatch(request, *args, **kwargs)
    
# Appointments admininistration view only accessible to:
# - Admin of the business with the event appointment
# - Appointment event workers
class AppointmentAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        appointment_id = kwargs.get('appointment_id')
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login') + '?next=' + request.path)
        if not request.user.customuser in appointment.event.account.admins.all() and request.user.customuser.id != appointment.worker.id:
            raise PermissionDenied("You are not an admin of this appointment.")
        return super().dispatch(request, *args, **kwargs)
    
class AppointmentWizardAccessMixin:
    """
    A mixin to control access to the BookingCreateWizardView based on user roles and their relationship to business and event entities.

    client_appointment urls are open for clients. This mixin ensures for appointment_wizard url:
    - For the base URL (only business_id provided), the user must be an authenticated admin of the specified business.
    - For the URL including an event_id, the user must be an authenticated worker of the specified event which must belong to the specified business.
    - For the URL including both event_id and worker_id, the user must be the specified worker, authenticated, and part of the event's workforce, with the event belonging to the specified business.

    The mixin raises a PermissionDenied exception if any of these conditions are not met, effectively restricting access to the view based on these stringent checks.
    """
    def dispatch(self, request, *args, **kwargs):
        # Client appointments urls are open
        if self.client_appointment:
            return super().dispatch(request, *args, **kwargs)
        
        business_handler = kwargs['business_handler']
        business = get_object_or_404(Account, handler=business_handler)
        business_id = business.id     

        event_handler = kwargs.get('event_handler', None)
        event_id = None
        if event_handler:
            event = get_object_or_404(Event, handler=event_handler)
            event_id = event.id     

        worker_id = kwargs.get('worker_id', None)
        
        # Check if the user is an admin for the first URL pattern
        if not event_id and not worker_id:
            if not request.user.is_authenticated or request.user.customuser not in business.admins.all():
                raise PermissionDenied("You are not an admin of this business.")
        
        # Check if the user is an event worker for the second URL pattern
        if event_id and not worker_id:
            event = get_object_or_404(Event, pk=event_id, account=business)
            if not request.user.is_authenticated or request.user.customuser not in event.event_workers.all():
                raise PermissionDenied("You are not a worker for this event.")

        # Check if the worker_id matches the logged-in user and belongs to the event for the third URL pattern
        if worker_id:
            event = get_object_or_404(Event, pk=event_id, account=business)
            if not request.user.is_authenticated or request.user.customuser.id != worker_id or request.user.customuser not in event.event_workers.all():
                raise PermissionDenied("Access denied for this operation.")
        
        return super().dispatch(request, *args, **kwargs)

class AdminRequiredForBusinessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not self.show_web:
            business_id = kwargs.get('business_id')
            business = get_object_or_404(Account, pk=business_id)
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse('login') + '?next=' + request.path)
            if not request.user.customuser in business.admins.all():
                raise PermissionDenied("You are not an admin of this business.")
        return super().dispatch(request, *args, **kwargs)

@business_admin_required 
def delete_business(request, business_id):
    business = get_object_or_404(Account, pk=business_id)
    try:
        business.delete()
        return JsonResponse({'message': 'Business deleted successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@user_is_event_admin
def add_event_location(request, event_id):
    if request.method == 'POST':
        address = request.POST.get('address')
        city = request.POST.get('city')
        province = request.POST.get('province')
        country = request.POST.get('country')
        
        if address and city and province and country:
            new_address = Address.objects.create(
                address=address,
                city=city,
                province=province,
                country=country
            )
            event = Event.objects.get(pk=event_id)
            event.locations.add(new_address)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@user_is_event_admin
def update_event_status(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        active = request.POST.get('active') == 'true'
        try:
            event = Event.objects.get(id=event_id)
            event.active = active
            event.save()
            return JsonResponse({'message': 'Event status updated successfully'}, status=200)
        except Event.DoesNotExist:
            return JsonResponse({'error': 'Event not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# Removes a worker from an event
@require_POST
@user_is_event_admin
def event_remove_worker(request, event_id, user_id):
    try:
        event = get_object_or_404(Event, id=event_id)
        user = get_object_or_404(CustomUser, id=user_id)
        
        # Remove the worker from the event if they are part of it
        if user in event.event_workers.all():
            event.event_workers.remove(user)
            message = "Worker removed successfully"
            status = 200
        else:
            message = "Worker not associated with this event"
            status = 400
    except Exception as e:
        message = str(e)
        status = 500

    return JsonResponse({'message': message}, status=status)
 
@user_is_event_admin
def add_event_question(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    event_page_options = get_object_or_404(EventPageOptions, event=event)

    if request.method == 'POST':
        question_form = EventQuestionForm(request.POST)
        answer_form = EventAnswerForm(request.POST)
        if question_form.is_valid() and answer_form.is_valid():
            question = question_form.save(commit=False)
            question.event_page_options = event_page_options
            question.save()

            answer = answer_form.save(commit=False)
            answer.question = question

            # Combine multiple 'options' parameters into a list and save as JSON
            options = request.POST.getlist('options')
            try:
                answer.options = json.dumps(options)
                print(answer.options)
            except ValueError as e:
                return JsonResponse({'success': False, 'errors': {'options': str(e)}}, status=400)            

            answer.save()

            return JsonResponse({'success': True, 'message': 'Question added successfully'})
        else:
            errors = {**question_form.errors, **answer_form.errors}
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        
@user_is_event_admin
def edit_question(request, event_id, question_id):
    question = get_object_or_404(EventPageQuestion, pk=question_id, event_page_options__event_id=event_id)
    event_page_options = get_object_or_404(EventPageOptions, event=question.event_page_options.event)

    if request.method == 'POST':
        question_form = EventQuestionForm(request.POST, instance=question)
        answer_form = EventAnswerForm(request.POST, instance=question.answers.first())
        
        if question_form.is_valid() and answer_form.is_valid():
            question_form.save()
            
            answer = answer_form.save(commit=False)
            options = request.POST.getlist('options')
            try:
                answer.options = json.dumps(options)
            except ValueError as e:
                return JsonResponse({'success': False, 'errors': {'options': str(e)}}, status=400)
            
            answer.save()

            return JsonResponse({'success': True, 'message': 'Question updated successfully'})
        else:
            errors = {**question_form.errors, **answer_form.errors}
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    
@user_is_event_admin
def remove_event_question(request, event_id, question_id):
    try:
        question = get_object_or_404(EventPageQuestion, pk=question_id, event_page_options__event_id=event_id)
        question.delete()
        return JsonResponse({'success': True, 'message': 'Question deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@user_is_event_admin
def event_question(request, event_id, question_id):
    try:
        question = get_object_or_404(EventPageQuestion, pk=question_id, event_page_options__event_id=event_id)
        data = model_to_dict(question)

        if question.answers.exists():
            answer = question.answers.first()
            options = json.loads(answer.options)
            data['answer_type'] = answer.answer_type
            data['options'] = json.loads(options[0]) if len(options) > 0 else []

        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

# Only admins of the business that the event belongs to are allowed to access this view    
class EventDetailView(EventAccessMixin, View):

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        event_ui, created = EventUI.objects.get_or_create(event=event)
        event_page_options, options_created = EventPageOptions.objects.get_or_create(event = event)
 
        if not event_ui.image:
            event_ui.image_url = static('img/event/placeholder.jpg')
        else:
            event_ui.image_url = event_ui.image.url

        event_configuration_status = EventConfigurationStatus(event)
        relative_event_url = reverse('client_appointment_for_event', args=[event.account.handler, event.handler])
        event_url = request.build_absolute_uri(relative_event_url)

        relative_web_url = reverse('web_business', args=[event.account.handler])
        web_url = self.request.build_absolute_uri(relative_web_url)
        questions = event_page_options.questions.all()

        return render(request, 
                      'events/event_details.html', 
                      {'event': event,
                       'event_ui': event_ui,
                       'event_page_options' : event_page_options,
                       'event_configuration_status': event_configuration_status,
                       'event_url': event_url,
                       'web_url': web_url,
                       'questions': questions,
                       'question_form': EventQuestionForm(),
                       'answer_form': EventAnswerForm(),                       
                       })

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        event_ui = EventUI.objects.get(event=event)
        
        # Update event fields with data from request
        event.name = request.POST.get('name', event.name)
        event.presentation = request.POST.get('presentation', event.presentation)
        event.notes = request.POST.get('notes', event.notes)
        event.duration = int(request.POST.get('duration', event.duration))
        event.time_slot_duration = int(request.POST.get('time-slots', event.time_slot_duration))

        workerIds = json.loads(request.POST.get('worker_ids'))        
        workers = CustomUser.objects.filter(pk__in=workerIds)
        event.event_workers.set(workers)

        # Update EventUI model
        event_ui.is_visible = request.POST.get('is_visible') == 'true'
        event_ui.description = request.POST.get('description', event_ui.description)

        # Handle image file upload
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            if image_file.size > 512000:
                return JsonResponse({'success': False, 'message' : 'File size exceeds 0.5MB. Please upload a smaller file.'})
            event_ui.image = image_file

        # Save changes
        event_ui.save()
        event.save()
        event_configuration_status = EventConfigurationStatus(event)
        return JsonResponse({'success': True,'message': 'Event updated successfully', 
                             'event_configuration_status': event_configuration_status.to_dict() }, 
                             status=200)

    def delete(self, request, pk):
        try:
            event = get_object_or_404(Event, pk=pk)
            event.delete()
            return JsonResponse({'message': 'Event deleted successfully'}, status=204)  # No Content
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True  # Redirect users who are already logged in
    next_page = reverse_lazy('dashboard')  # Redirect to dashboard after login

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial_username = self.request.GET.get('un', None)
        
        if initial_username:
            if 'form' in context:
                context['form'].fields['username'].initial = initial_username
        return context
    
class LoggedOutView(TemplateView):
    template_name = 'registration/logged_out.html'

# Return the business where the logged in user is an admin
class AccountListView(LoginRequiredMixin, ListView):
    show_dropdown = False
    model = Account
    context_object_name = 'accounts'

    def get(self, request, *args, **kwargs):
        # Get the user's accounts
        user_accounts = self.get_queryset()
        # If only one account is assigned, redirect to that account's detail page
        if user_accounts.count() == 1 and self.show_dropdown:
            return redirect('appointment_wizard', business_handler=user_accounts.first().handler) 
        
        # Otherwise, continue with the normal flow
        return super(AccountListView, self).get(request, *args, **kwargs)

    def get_template_names(self):
        if self.show_dropdown:
            return ['business/business_list_for_appointment.html']
        else:
            self.paginate_by = 10
            return ['business/business_list.html']

    def get_queryset(self):
        user = CustomUser.objects.get(user=self.request.user)
        return Account.objects.filter(admins=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user_businesses = self.get_queryset()
        businesses_configuration = []
        for business in user_businesses:
            business_configuration = BusinessConfigurationStatus(business)
            businesses_configuration.append(business_configuration)

        context['businesses_configuration'] = businesses_configuration
        return context

class SpecialDayView(BusinessAccessMixin, View):
    def post(self, request, *args, **kwargs):

        special_day_id = kwargs.get('id')
        account_id = kwargs.get('business_id')

        date = request.POST.get('date')
        closed = request.POST.get('closed', False)
        from_hour = request.POST.get('from_hour')
        to_hour = request.POST.get('to_hour')

        if special_day_id:
            # Update existing SpecialDay
            try:
                special_day = SpecialDay.objects.get(pk=special_day_id)
                special_day.date = date
                special_day.closed = closed
                special_day.from_hour = from_hour
                special_day.to_hour = to_hour
            except SpecialDay.DoesNotExist:
                return HttpResponseNotFound(json.dumps({'error': 'SpecialDay not found'}), content_type="application/json")
        else:
            # Create new SpecialDay
            account = get_object_or_404(Account, pk=account_id)
            special_day = SpecialDay(account=account, date=date, closed=closed, from_hour=from_hour, to_hour=to_hour)

        special_day.save()
        return JsonResponse({'success': True, 'id': special_day.id})

    def delete(self, request, *args, **kwargs):
        special_day_id = kwargs.get('id')
        if special_day_id is not None:
            special_day = get_object_or_404(SpecialDay, pk=special_day_id)
            special_day.delete()
            return JsonResponse({'success': True})
        else:
            return HttpResponseBadRequest(json.dumps({'error': 'Missing SpecialDay id'}), content_type="application/json")

class BusinessHourView(BusinessAccessMixin, View):
    def post(self, request, *args, **kwargs):

        hour_id = kwargs.get('id', None)
        account_id = kwargs.get('business_id', None)
        weekday = request.POST.get('weekday')
        from_hour = request.POST.get('from_hour')
        to_hour = request.POST.get('to_hour')

        if hour_id:
            # Update existing hour
            opening_time = get_object_or_404(OpenningTime, pk=hour_id)
            opening_time.weekday = weekday
            opening_time.from_hour = from_hour
            opening_time.to_hour = to_hour
        else:
            # Create new hour
            account = get_object_or_404(Account, pk=account_id)
            opening_time = OpenningTime(account=account, weekday=weekday, from_hour=from_hour, to_hour=to_hour)
        
        opening_time.save()
        return JsonResponse({'success': True, 'hour_id': opening_time.pk})

    def delete(self, request, id, *args, **kwargs):
        print(f'---------> {id}' )
        opening_time = get_object_or_404(OpenningTime, pk=id)
        opening_time.delete()
        return JsonResponse({'success': True})
    
def send_cancellation_email(appointment, reason):
    for invitee in appointment.invitees.all():
        subject = f"Your reservation with {appointment.event.account.name} has been cancelled"

        plain_message = f"""
        Hello {invitee.name},

        We inform you that your appointment at {appointment.event.account.name} has been cancelled. 

        These are the details of the appointment that has been cancelled:

        - Event: {appointment.event.name}
        - Date: {appointment.date}
        - Time: {appointment.time}
        - Reason: {reason}

        If you think this might be an error, please contact the business or book online again with them.

        Best Regards,
        The ReservaClick Team
        """

        html_message = f"""
            <p>Hello <strong>{ invitee.name }</strong>,</p>

            <p>We inform you that your appointment at <strong>{ appointment.event.account.name }</strong> has been cancelled.</p>

            <p>These are the details of the appointment that has been cancelled:</p>
            <ul>
                <li>Event: <strong>{ appointment.event.name }</strong></li>
                <li>Date: <strong>{ appointment.date }</strong></li>
                <li>Time: <strong>{ appointment.time }</strong></li>
                <li>Reason: <strong>{ reason }</strong></li>
            </ul> 

            <p>If you think this might be an error, please contact the business or book online again with them.</p>

            <p>Best Regards,<br>
            The ReservaClick Team</p>
        """

        send_mail(            
            subject=subject,
            message=plain_message,
            from_email= f"ReservaClick <{settings.EMAIL_HOST_USER}>",
            recipient_list=[invitee.email],
            html_message=html_message
        )   

class AppointmentView(AppointmentAccessMixin, View):
    show_cancel_button = False
    
    def get(self, request, *args, **kwargs):
        appointment_id = kwargs.get('appointment_id')
        appointment = get_object_or_404(Appointment, id=appointment_id)
        return render(request, 'appointments/appointment_detail.html', {
            'appointment': appointment,
            'show_cancel_button': self.show_cancel_button
        })

    def post(self, request, *args, **kwargs):
        appointment_id = request.POST.get('appointment_id')
        reason = request.POST.get('reason')
        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.status != 'CANCELLED':
            appointment.status = 'CANCELLED'
            appointment.save()
            cancellation, created = AppointmentCancellation.objects.get_or_create(appointment_id=appointment_id)
            cancellation.cancellation_time = timezone.now()
            cancellation.cancelled_by = 'CLIENT'
            cancellation.reason = request.POST.get('reason') or ''
            cancellation.save()
            # Send cancellation emails to all invitees to this event.
            send_cancellation_email(appointment, reason)
            response = {'status': 'success', 'message': 'Appointment cancelled successfully'}
        else:
            response = {'status': 'failed', 'message': 'Appointment already cancelled'}
        return JsonResponse(response)
    

class BusinessWorkerView(BusinessAccessMixin, View):
    show_remove_button = False
    
    def get(self, request, *args, **kwargs):
        worker_id = kwargs.get('worker_id')
        account_id = kwargs.get('business_id')
        worker = get_object_or_404(CustomUser, id=worker_id)
        account = get_object_or_404(Account, id=account_id)
        if worker in account.account_workers.all():
            # Events the worker has assign for a particular business
            events = Event.objects.filter(account_id=account_id, event_workers__id=worker_id)
            # Appointments for that user for this business in the next 30 days
            today = datetime.today()
            end_date = today + timedelta(days=30)
            appointments = Appointment.objects.filter(status = 'ACTIVE',
                                                      worker_id = worker_id, 
                                                      event__account = account, 
                                                      date__gte = today, 
                                                      date__lte = end_date)
            
            # group appointments by date
            grouped_appointments = {}
            for appt in appointments:
                if appt.date in grouped_appointments:
                    grouped_appointments[appt.date].append(appt)
                else:
                    grouped_appointments[appt.date] = [appt]

            # Current Custom User
            current_user = CustomUser.objects.get(user=self.request.user)

            # NOTE: Domain to build the links to the events. Use full_event_url if domain doesn't work in production
            domain = get_current_site(self.request).domain
            full_event_url = self.request.build_absolute_uri(domain)          
            
            return render(request, 'worker_detail.html', {
                'worker': worker,
                'events': events,
                'appointments': grouped_appointments,
                'account': account,
                'show_remove_button': self.show_remove_button,
                'current_user' : current_user,
                'domain' : domain
            })
        else:
            raise Exception("Error: The worker is not assigned to the account")

    def post(self, request, *args, **kwargs):
        worker_id = self.kwargs['worker_id']
        business_id = self.kwargs['business_id'] 
        worker = get_object_or_404(CustomUser, id=worker_id)
        account = get_object_or_404(Account, id=business_id)
        if worker in account.account_workers.all():
            account.account_workers.remove(worker)
            for event in account.events.all():
                if worker in event.event_workers.all():
                    event.event_workers.remove(worker)
            response = {'status': 'success', 'message': 'Worker removed successfully from your business and any event associated with it.'}
        else:
            response = {'status': 'failed', 'message': 'Appointment already cancelled'}

        return JsonResponse(response)    

def addMins(tm, mins):
    fulldate = datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
    fulldate = fulldate + timedelta(minutes=mins)
    return fulldate.time()

def generate_time_slots(start_time, end_time, duration):    
    slots = []
    current_time = start_time
    while current_time < end_time:
        # Add the current time to the list of slots
        slots.append(current_time)
        # Increment the current time by the duration
        current_time = addMins(current_time, duration)
    
    return slots

def build_available_time_slots(business_id, event_id, worker_id, date_str):
    print(f'-------------> In build_available_time_slots. business_id: {business_id}, event_id:{event_id}, worker_id:{worker_id}, date_str:{date_str}')
    # Get the business info
    account = Account.objects.get(id=business_id)    

    # Get the event duration
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    event = Event.objects.get(id=event_id)
    event_duration = event.duration
    time_slot_duration = event.time_slot_duration

    # Get the account opening hours   
    opening_hours_list = OpenningTime.objects.filter(account=business_id, weekday=str(date.weekday()))

    if not opening_hours_list.exists():
        opening_hours_list = [
            OpenningTime(
                account=account,
                weekday=str(date.weekday()),
                from_hour=time(1, 0),
                to_hour=time(0, 0)
            )
        ]

    all_slots = set() 

    for opening_hours in opening_hours_list:
        slots = generate_time_slots(opening_hours.from_hour, opening_hours.to_hour, time_slot_duration)
        all_slots.update(slots)

    slots = sorted(all_slots)

        # Handle special days
    special_days = SpecialDay.objects.filter(account=business_id, date=date)

    for special_day in special_days:
        if special_day.closed:
            # If the whole day is closed, clear all slots
            slots = []
            break
        else:
            # Remove slots that fall within the special day's closed hours
            slots = [slot for slot in slots if not (special_day.from_hour <= slot < special_day.to_hour)]

    print(f'-------------------_> slots: {slots}')
    # Get the appointments the worker has for the date
    appointments = Appointment.objects.filter(worker = worker_id, date=date).all().order_by('time')

    # Find the slots that are not available
    busy_time_slots = []
    for appointment in appointments:
        appt_start = appointment.time
        appt_end = addMins(appt_start, appointment.event.duration)

        for slot in slots:
            potential_appt_start = slot
            potential_appt_end = addMins(potential_appt_start, event_duration)
            if slot not in busy_time_slots and potential_appt_end > appt_start and potential_appt_start < appt_end:
                busy_time_slots.append(slot)

    # Build the available time slots based on what is busy
    available_time_slots = []
    for slot in slots:
        taken = False
        if slot in busy_time_slots:
            taken = True

        available_time_slots.append(
            {"time": slot.strftime('%H:%M'), "is_taken": taken}
        )
    return available_time_slots

def get_available_time(request):
    response = []
    if request.method == 'GET':
        # Get the request params
        business_id = request.GET.get('business_id', '')
        event_id = request.GET.get('event_id', '')
        worker_id = request.GET.get('worker_id', '')
        date_str = request.GET.get('date', '')

        available_time_slots = build_available_time_slots(business_id, event_id, worker_id, date_str)

        return JsonResponse(available_time_slots, safe=False)
    
class CancelAppointmentEmail(View):
    template_name = 'appointments/appointment_cancel.html'
    confirmation_template_name = 'appointments/appointment_cancel_confirmation.html'

    def get(self, request, appointment_id, cancel_uuid):
        cancellation = get_object_or_404(AppointmentCancellation, appointment_id=appointment_id, cancel_uuid=cancel_uuid)
        appearance, created = BusinessAppearance.objects.get_or_create(account_id=cancellation.appointment.event.account.id)
        return render(request, self.template_name, {'appointment': cancellation.appointment,
                                                    'event': cancellation.appointment.event,
                                                    'appearance': appearance})

    def post(self, request, appointment_id, cancel_uuid):
        # Verify the UUID and get the appointment
        cancellation = get_object_or_404(AppointmentCancellation, appointment_id=appointment_id, cancel_uuid=cancel_uuid)
        appearance, created = BusinessAppearance.objects.get_or_create(account_id=cancellation.appointment.event.account.id)
        appointment = cancellation.appointment
        if appointment.status != 'CANCELLED':
            appointment.status = 'CANCELLED'
            appointment.save()
            cancellation.cancellation_time = timezone.now()
            cancellation.cancelled_by = 'CLIENT'
            cancellation.save()
            # NOTE: Reason field is not implemented in the UI so I am assigning an empty field for now
            send_cancellation_email(appointment, '')
            return render(request, self.confirmation_template_name, {'header': 'Appointment Cancelled',
                                                                    'message': 'Your appointment has been successfully cancelled.',
                                                                    'event': cancellation.appointment.event,
                                                                    'appearance': appearance})
        else:
            return render(request, self.confirmation_template_name, {'header': 'This appointment was already cancelled',
                                                                    'message': 'Feel free to book again if you need so',
                                                                    'appearance': appearance})


def event_inactive_view(request):
    return render(request, 'event_inactive.html')

def send_appointment_confirmation_email(to_client, event, appointment, request):
    cancel_appt_url = reverse('appointment_email_cancel', args=[appointment.id, appointment.cancellation.cancel_uuid])
    cancel_appt_url = request.build_absolute_uri(cancel_appt_url)

    subject = 'Your appointment with ' + event.account.name + ' | ' + event.name
    message = 'Your appointment ' + event.name + ' at ' + event.account.name + ' with ' + appointment.worker.user.first_name + ' ' + \
                appointment.worker.user.last_name + ' is on ' + appointment.date.strftime('%d-%m-%Y') +' at ' + appointment.time.strftime('%H:%M:%S')  + ' .'
    
    if not to_client:
        subject = 'Congrats, you have a new appointment at ' + event.account.name + ' | ' + event.name
        message = 'Your appointment ' + event.name + ' at ' + event.account.name + ' with ' 
        for invitee in appointment.invitees.all():
            message += invitee.name + ' '        
        message +=' is on ' + appointment.date.strftime('%d-%m-%Y') +' at ' + appointment.time.strftime('%H:%M:%S')  + ' .'

    html_message = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                background-color: #f4f4f4;
                color: #333;
                line-height: 1.6;
                padding: 20px;
            }}
            .content {{
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                margin: auto;
                width: 100%;
                max-width: 600px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center; /* Centers the text for the whole content div */
            }}
            .details-card {{
                background-color: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                border: 2px solid #ccc; /* Adds a light grey border */
            }}
            .appointment-details {{
                font-size: 16px;
                margin-bottom: 10px;
                text-align: left; /* Aligns text to the left within the card */
            }}
            .highlight {{
                color: #007bff;
                font-weight: bold;
                font-size: 18px;
            }}
            .button {{
                display: block; /* Makes the button a block element to fill the width of its container */
                width: 50%;
                min-width: 180px; /* Ensures the button is not too narrow on smaller screens */
                height: 35px;
                background-color: #ccc;
                color: #333;
                border-radius: 5px;
                text-decoration: none;
                line-height: 35px;
                font-size: 14px;
                margin: 10px auto 20px; /* Centers the button horizontally */
            }}
            .cancel-text {{
                font-size: 12px;
                text-align: center;
                margin-top: 20px;
                margin-bottom: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="content">
        """
    if to_client:
        html_message += f"""
            <h2>Thank You and Congratulations!</h2>
            <p>We are pleased to confirm your appointment. Here are the details:</p>
            """
    else:
        html_message += f"""
            <h2>Congratulations on your new appointment!</h2>
            <p>Here are the details:</p>
            """
    html_message += f"""               
            <div class="details-card">
                <div style="text-align:center">
                    <h1>{event.account.name}</h1>
                </div>
                <p class="appointment-details">Your appointment: <span class="highlight">{event.name}</span></p>
                <p class="appointment-details">Location: <span class="highlight">{event.account.address.address}, {event.account.address.city}</span></p>
                """
    if to_client:
        html_message += f"""
            <p class="appointment-details">With: <span class="highlight">{appointment.worker.user.first_name} {appointment.worker.user.last_name}</span></p>
            """
    else:
        html_message += '<p class="appointment-details">Customer: <span class="highlight">'
        for invitee in appointment.invitees.all():
            html_message += invitee.name + ' '
            
        message += '</span></p>'
    
    html_message += f"""
                <p class="appointment-details">Date: <span class="highlight">{appointment.date.strftime('%d-%m-%Y')}</span></p>
                <p class="appointment-details">Time: <span class="highlight">{appointment.time.strftime('%H:%M:%S')}</span></p>
            </div>
            """
    if to_client:
        html_message += f"""
            <p class="cancel-text">Do you need to cancel this appointment?</p>
            <a href="{cancel_appt_url}" class="button">Cancel Appointment</a>
            """
    html_message += f"""
            </div>
    </body>
    </html>
    """

    print(f'****************************The link is: {cancel_appt_url}')

    # Send email to clients to confirm the reservation
    for invitee in appointment.invitees.all():
        send_mail(            
            subject=subject,
            message=message,
            from_email= f"{event.account.name} via ReservaClick <{settings.EMAIL_HOST_USER}>",
            recipient_list=[invitee.email],
            html_message=html_message
        )

# Create your views here.
APPOINTMENT_STEP_FORMS = (
    ('Event', SelectEventForm),
    ('Worker', SelectWorkerForm),
    ('DateTime', SelectDateTimeForm),
    ('CustomerInfo', CustomerInformationForm)
)

class BookingCreateWizardView(AppointmentWizardAccessMixin, SessionWizardView):
    template_name = "appointments/appointment_wizard.html"
    form_list = APPOINTMENT_STEP_FORMS    
    progress_width = 25
    booking_page_subheading = ''
    initial_dict = { }
    client_appointment = False
    base_template = 'appointments/base.html'
    print('---------------------------////////////////////)))))))))))))))))))))))))))))))')

    def get_context_data(self, form, **kwargs):    
        print('-------------------- get_context_data')    
        context = super().get_context_data(form=form, **kwargs)
        # This is the base template of the appointment_wizard. If it is the client making the appointment we will change this base        
        if self.client_appointment:
            self.base_template = 'appointments/base_client_appointment.html'

        print(f'client_appointment: {self.client_appointment}')
        print(f'base_template: {self.base_template}')

        time_list = []
        if self.steps.current == 'DateTime':
            time_list= []

        business_id = None
        event_id = None
        worker_id = None
        if 'Event' in self.initial_dict:
            business_id = self.initial_dict['Event'].get('business_id')
            print('----------------- business_id: ' + str(business_id))

        if 'Worker' in self.initial_dict:
            event_id = self.initial_dict['Worker'].get('event_id')
            print('----------------- event_id: ' + str(event_id))

        if 'DateTime' in self.initial_dict:
            worker_id = self.initial_dict['DateTime'].get('worker_id')
            print('----------------- worker_id: ' + str(worker_id))
        
        if business_id != None and event_id != None and worker_id != None:
            today = datetime.today().strftime('%Y-%m-%d')
            time_list = build_available_time_slots(business_id, event_id, worker_id, today)

        # Make sure that business_id is always populted at this point
        business = Account.objects.get(pk=business_id)
        appearance, created = BusinessAppearance.objects.get_or_create(account_id=business_id)
        appointment_description = 'Select your Appt'
        notes = ''
        if event_id:
            event = Event.objects.get(id=event_id)
            appointment_description = event.name
            notes = event.notes

        context.update({
            "progress_width": self.progress_width,
            "booking_bg": 'booking_bg.jpg',
            "description": appointment_description,
            "notes": notes,
            "title": business.name,
            "get_available_time" : time_list,
            "business_id" : business_id,
            "event_id" : event_id,
            "worker_id" : worker_id,
            "client_appointment" : self.client_appointment,
            "base_template" : self.base_template,
            "appearance" : appearance,
            'booking_page_subheading': self.booking_page_subheading,
            'booking_page_heading' : self.booking_page_heading
        })

        return context
    
    def get_form(self, step=None, data=None, files=None):
        print('---------------------------////////////////////')
        form = super().get_form(step, data, files)
        step = step or self.steps.current
        print('-----------> In get_form')
        if 'event_handler' in self.kwargs:
            event_handler = self.kwargs['event_handler']
            event = get_object_or_404(Event, handler=event_handler)
            event_id = event.id                
            if not event.active:
                return InactiveEventForm()
            elif step == 'CustomerInfo':
                form = CustomerInformationForm(data=data, event=event)
            
        return form
                    
    def get_form_initial(self, step):
        # Determine the type of Wizard.
        # Only business_id info -> Complete wizard: Select Event, Worker, Time and User Info
        # business_id and event_id -> Select Worker, Time and Info
        # business_id, event_id and worker_id selected -> Select Time and Info
        print('---------------------------////////////////////')
        business_handler = self.kwargs['business_handler']
        business = get_object_or_404(Account, handler=business_handler)
        business_id = business.id

        event_id = None
        if 'event_handler' in self.kwargs:
            event_handler = self.kwargs['event_handler']
            event = get_object_or_404(Event, handler=event_handler)
            event_id = event.id 
            
        worker_id = None
        if 'worker_id' in self.kwargs:
            worker_id = self.kwargs['worker_id']

        print(f"business_id: {business_id}")
        print(f"event_id: {event_id}")

        if step == 'Event':
            print('In get form initial - Event')           
            self.initial_dict['Event'] = {'business_id': business_id}
        elif step == 'Worker': 
            print('In get form initial - Worker')
            # Get the event_id from url or from the post request
            # If event_id is coming from the url then set event key so the state of the class is the same as if all screens are executed
            if event_id:
                self.initial_dict['Event'] = {'business_id': business_id}
                self.initial_dict['Worker'] = {'event_id': event_id} 
            elif 'Event-events' in self.request.POST:
                self.initial_dict['Worker'] = {'event_id': self.request.POST.get('Event-events')} 
        elif step == 'DateTime':
            # If event_id is coming from the url then set event and worker keys so the state of the class is the same as if all screens are executed
            if worker_id:
                self.initial_dict['DateTime'] = {'worker_id': worker_id} 
                self.initial_dict['Event'] = {'business_id': business_id}
                self.initial_dict['Worker'] = {'event_id': event_id} 
            elif 'Worker-workers' in self.request.POST:
                self.initial_dict['DateTime'] = {'worker_id': self.request.POST.get('Worker-workers')} 

        return self.initial_dict

    def render(self, form=None, **kwargs):    
        print('kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        form = form or self.get_form()        
        
        if self.steps.current == 'Event':
            self.progress_width = 5
            self.booking_page_heading = 'Events'
            self.booking_page_subheading = 'Select the event you want.'
        elif self.steps.current == 'Worker':
            self.progress_width = 25   
            self.booking_page_heading = 'Staff'
            self.booking_page_subheading = 'Select one of our staff members.' 
        elif self.steps.current == 'DateTime':
            self.progress_width = 50    
            self.booking_page_heading = 'Day and Time'
            self.booking_page_subheading = 'Select the day and time of your appointment.'
        elif self.steps.current == 'CustomerInfo':
            self.progress_width = 75   
            self.booking_page_heading = 'Customer Info'
            self.booking_page_subheading = 'Complete this information.'
        
        context = self.get_context_data(form=form, **kwargs)    

        if isinstance(form, InactiveEventForm):
            # Adjust template or context if showing the inactive event form
            print('Returning event inactive form')
            self.template_name = "appointments/event_inactive.html"

        return self.render_to_response(context)
    
    def done(self, form_list, **kwargs):
        data = dict((key, value) for form in form_list for key,
                    value in form.cleaned_data.items())
        print(':::::::::::::::::::::::::::::')
        print(data)
        print(':::::::::::::::::::::::::::::')

        event_id = None
        if 'event_handler' in self.kwargs:
            event_handler = self.kwargs['event_handler']
            event = get_object_or_404(Event, handler=event_handler)
            event_id = event.id 
        else:
            event_id = data['events']

        worker_id = None
        if 'worker_id' in self.kwargs:
            worker_id = self.kwargs['worker_id']
        else:
            worker_id = data['workers']

        # Create the appointment
        invitee, created = Invitee.objects.get_or_create(
            email=data['user_email'],
            name=data['user_name'],
            phone_number=data['user_mobile']
        )

        if created:
            print(f"New invitee created: {invitee}")
        else:
            print(f"Invitee already exists: {invitee}")

        event = Event.objects.get(id = event_id)
        custom_user = CustomUser.objects.get(id = worker_id)
        appointment = Appointment(event = event, date = data['date'], time = data['time'], worker = custom_user, location='Default' )
        appointment.save()
        appointment.invitees.add(invitee)
        appointmentCancellation = AppointmentCancellation(appointment=appointment)
        appointmentCancellation.save()

        # Save responses to the questions
        for key, value in data.items():
            if key.startswith('question_'):
                question_id = key.split('_')[1]
                question = EventPageQuestion.objects.get(id=question_id)
                response = AppointmentQuestionResponse(appointment=appointment, question=question, response=value)
                response.save()

        # Send confirmation email to worker and clients
        send_appointment_confirmation_email(False,event, appointment, self.request)
        send_appointment_confirmation_email(True, event, appointment, self.request)

        if self.client_appointment:
            self.base_template = 'appointments/base_client_appointment.html'
            
        business_handler = self.kwargs['business_handler']
        business = get_object_or_404(Account, handler=business_handler)
        business_id = business.id
        appearance, created = BusinessAppearance.objects.get_or_create(account_id=business_id)

        return render(self.request, 'appointments/appointment_done.html', {
            "progress_width": "100",
            "event" : event,
            "appointment" : appointment,
            "invitee" : invitee,
            "description": event.name,
            "title": event.account.name,
            "base_template": self.base_template,
            'appearance': appearance
        })        

# Personal dashboard for users. It requires the user to be logged in.
# The response is based on the logged user so they can't access any other info altering the url
# Returns:
# - Accounts the user is an admin
# - Appointments the user has in the following 30 days 
class DashboardView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    context_object_name = 'accounts'
    template_name = 'users/dashboard.html'

    def get_queryset(self):
        queryset = Account.objects.filter(admins__id= self.request.user.id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.today()
        end_date = today + timedelta(days=30)
        appointments = Appointment.objects.filter(status = 'ACTIVE',
                                                  worker__id = self.request.user.id, 
                                                  date__gte = today, 
                                                  date__lte = end_date).order_by('date')
        # group appointments by date
        grouped_appointments = {}
        for appt in appointments:
            if appt.date in grouped_appointments:
                grouped_appointments[appt.date].append(appt)
            else:
                grouped_appointments[appt.date] = [appt]
        context['appointments'] = grouped_appointments

        businesses_user_is_working_for = Account.objects.filter(
                                            account_workers=self.request.user.customuser
                                        ).exclude(
                                            admins=self.request.user.customuser
                                        )
        context['businesses_user_is_working_for'] = businesses_user_is_working_for
        return context
    
class EventsView(ListView):
    context_object_name = 'events'
    template_name = 'events/events_list.html'

    def get_queryset(self):
        current_user = CustomUser.objects.get(user=self.request.user)

        # Query to find all events where the user is an admin in the account of the event
        #admin_events = Event.objects.filter(account__admins=current_user)      

        # Query to find all events where the user is listed as an event worker
        #worker_events = Event.objects.filter(event_workers=current_user)  

        all_user_events = Event.objects.filter(
            Q(account__admins=current_user) | Q(event_workers=current_user)
        ).distinct()

        return all_user_events
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_user = CustomUser.objects.get(user=self.request.user)

        # Query to find all Accounts where the current_user is an admin
        accounts_as_admin = Account.objects.filter(admins=current_user)

        # Query to find all Accounts associated with Events where the current_user is a worker
        accounts_as_event_worker = Account.objects.filter(
            events__event_workers=current_user
        ).distinct()

        # Combine both queries to get a unique set of Accounts
        user_related_accounts = Account.objects.filter(
            Q(id__in=accounts_as_admin) | Q(id__in=accounts_as_event_worker)
        ).distinct()

        current_user = CustomUser.objects.get(user=self.request.user)

        # NOTE: Domain to build the links to the events. Use full_event_url if domain doesn't work in production
        domain = get_current_site(self.request).domain
        full_event_url = self.request.build_absolute_uri(domain)

        context['businesses'] = user_related_accounts
        context['current_user'] = current_user
        context['domain'] = domain

        return context

def user_registration(request):
    initial_data = {}
    next_url = request.GET.get('next', '')

    if 'email' in request.GET:
        initial_data['email'] = request.GET['email']

    if request.method == 'POST':  
        form = SignUpForm(request.POST)          
        if form.is_valid():  
            user = form.save() 

            # Send confirmation email
            subject = "Welcome to ReservaClick - In 15m your online presence and booking page ready"

            plain_message = f"""
            Hello {user.first_name},

            Thank you for choosing ReservaClick for your online presense and booking needs.

            We are thrilled to have you here. Our team is already working to help you.

            Thank you for your trust in ReservaClick.

            Best Regards,
            The ReservaClick Team
            """

            html_message = f"""
                <p>Hello {user.first_name},</p>
                <p>Thank you for choosing ReservaClick for your online presense and booking needs.</p>
                <p>We are thrilled to have you here. Our team is already working to help you.</p>
                <p>Thank you for your trust in ReservaClick. </p>
                <br>
                <p>Best Regards,</p>
                <p>The ReservaClick Team</p>
            """

            send_mail(            
                subject=subject,
                message=plain_message,
                from_email= f"ReservaClick <{settings.EMAIL_HOST_USER}>",
                recipient_list=[user.email],
                html_message=html_message
            )      

            redirect_url = reverse('user_login') if not next_url else next_url
            return redirect(redirect_url)
    else:  
        form = SignUpForm(initial=initial_data)
    context = {  
        'form':form  
    }  
    return render(request, 'registration/user_registration.html', context)     

@login_required
def add_business(request):
    if request.method == 'POST':
        form = CreateAccountForm(request.POST)
        address_form = AddressForm(request.POST)
        if form.is_valid() and address_form.is_valid():
            # First save the address to obtain an instance
            new_address = address_form.save()
            # Save the form to create an Account object but do not commit to the database yet
            new_account = form.save(commit=False)
            new_account.address = new_address
            new_account.save()  # Save the new Account object to the database
            # Add the current user as an admin and a worker of the new account
            new_account.admins.add(CustomUser.objects.get(user=request.user))
            new_account.account_workers.add(request.user.customuser)
            # If there are many-to-many fields included in the form, save the form with commit=True to save those relationships
            form.save_m2m()

            # Create and link an AccountUI object to the newly created account
            account_ui = AccountUI.objects.create(
                business=new_account,
                is_visible=False,  # Set default visibility or modify as needed
                description=''  # Set a default description or leave blank to update later
            )

            # Create and link a new BusinessApearance object
            business_appearance = BusinessAppearance.objects.create(account=new_account)
            return redirect('business-list')
    else:
        form = CreateAccountForm()
        address_form = AddressForm()

    context = {'form': form, 'address_form': address_form}
    return render(request, 'business/add_business.html', context)

# Renders the public user business website or the business admin page
# If the view is for the public user business there should not be any authentication required
# If the view is for the business admin page then the user must be authenticated and must be business admin    
class ViewBusiness(AdminRequiredForBusinessMixin, TemplateView):
    show_web = False
    def get_template_names(self):
        if self.show_web:
            return ['web/home.html']
        else:
            return ['business/view_business.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        business = None
        if self.show_web:
            business_handler = self.kwargs.get('business_handler', None)
            business = get_object_or_404(Account, handler=business_handler)
        else:
            business_id = self.kwargs.get('business_id', None)
            business = get_object_or_404(Account, id=business_id)
    
        business_ui, created = AccountUI.objects.get_or_create(business=business)
        if not business_ui.header_image:
            business_ui.header_image_url = static('img/business/placeholder.jpg')
        else:
            business_ui.header_image_url = business_ui.header_image.url

        business_hours = OpenningTime.objects.filter(account=business.id)
        special_days = SpecialDay.objects.filter(account=business.id)
        events = Event.objects.filter(account_id=business.id)
        if self.show_web:
            events = Event.objects.filter(account_id=business.id, ui__is_visible = True)

        businesses_configuration = BusinessConfigurationStatus(business)
        relative_web_url = reverse('web_business', args=[business.handler])
        web_url = self.request.build_absolute_uri(relative_web_url)

        # Format business hours and special days times
        for business_hour in business_hours:
            business_hour.to_hour = business_hour.to_hour.strftime('%H:%M')
            business_hour.from_hour = business_hour.from_hour.strftime('%H:%M')

        for special_day in special_days:
            special_day.to_hour = special_day.to_hour.strftime('%H:%M')
            special_day.from_hour = special_day.from_hour.strftime('%H:%M')

        for event in events:
            relative_event_url = reverse('client_appointment_for_event', args=[event.account.handler, event.handler])
            event.event_url = self.request.build_absolute_uri(relative_event_url)
            if not event.ui.image:
                event.ui.image_url = static('img/event/placeholder.jpg')
            else:
                event.ui.image_url = event.ui.image

        workers = business.account_workers.all()
        for worker in workers:
            if not worker.profile_image:
                worker.profile_image_url = static('img/user_profile/placeholder.jpg')
            else:
                worker.profile_image_url = worker.profile_image

        context.update({
            'business': business,
            'business_ui': business_ui,
            'business_hours': business_hours,
            'special_days': special_days,
            'events': events,
            'available_days': WEEKDAYS,
            'gm_key': settings.GM_KP,
            'businesses_configuration': businesses_configuration,
            'web_url': web_url,
            'workers': workers
        })

        return context

@business_admin_required
def add_business_event(request, business_id = -1):
    business = get_object_or_404(Account, pk=business_id)
    if request.method == 'POST':
        form = CreateEventForm(request.POST, account_id=business_id)
        if form.is_valid():
            try:
                new_event = form.save(commit=False)
                new_event.account = business
                new_event.save()

                # Create EventPageOptions object
                event_page_options = EventPageOptions(event=new_event)
                event_page_options.save()
                
                # Create EventUI object
                event_ui = EventUI(event=new_event)
                event_ui.save()

                form.save_m2m()
                return redirect('view_business', business_id = business_id)
            except ValueError as e:  
                print('-----------------------------> ' + str(e))
                form.add_error(None, str(e))      
        else:
            print('----------------------> HERE')  
        
    elif request.method == 'GET':
        form = CreateEventForm(account_id=business_id) 

    context = {
        'form': form,
        'business': business
        }
    return render(request, 'events/add_event.html', context)
    
@require_POST
@user_is_event_admin
def toggle_event_active(request):
    event_id = request.POST.get('event_id')
    event = get_object_or_404(Event, id=event_id)
    event.active = not event.active
    event.save()
    return JsonResponse({'status': 'success', 'event_active': event.active})

@require_POST
@business_admin_required
def update_business_address(request, business_id):
    try:
        account = get_object_or_404(Account, pk=business_id)
        account.address.address = request.POST.get('address')
        account.address.city = request.POST.get('city')
        account.address.province = request.POST.get('province')
        account.address.country = request.POST.get('country')
        account.address.save()      
        return JsonResponse({'success': True, 'message': 'Business UI updated successfully'})  
    except Http404:
        # Return a JSON response if the object is not found
        data = {'success': False, 'message': 'Business not found.'}
   


@require_POST
@business_admin_required
def update_business_ui(request, business_id):
    try:
        # Get the account instance
        account = get_object_or_404(Account, pk=business_id)
        
        # Get the associated UI instance or create a new one if it doesn't exist
        account_ui, created = AccountUI.objects.get_or_create(business=account)
        
        # Update the UI visibility
        account_ui.is_visible = request.POST.get('is_visible') == 'true'

        # Handle the header image upload
        header_image = request.FILES.get('business_header_image')
        if header_image:
            if header_image.size > 512000:
                return JsonResponse({'success': False, 'message' : 'Image file size exceeds 0.5MB. Please upload a smaller file.'})     
            
            # Save the header image using the `account_directory_path` method
            account_ui.header_image.save(header_image.name, header_image)

        # Update general business description
        account_ui.description = request.POST.get('description')
        
        # Save the UI instance
        account_ui.save()

        # Return a response indicating success
        return JsonResponse({'success': True, 'message': 'Business UI updated successfully', 'is_visible': account_ui.is_visible, 'header_image_url': account_ui.header_image.url})
    except Http404:
        # Return a JSON response if the object is not found
        data = {'success': False, 'message': 'Business not found.'}

class UserProfileMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        
        # When show_web is True, GET is open to anyone, POST is not allowed
        if self.show_web:
            if request.method == "POST":
                return self.handle_no_permission()
            return super().dispatch(request, *args, **kwargs)

        # When show_web is False, both GET and POST require user to be the logged in user
        if not request.user.is_authenticated or str(request.user.customuser.id) != str(user_id):
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)
    
class UserProfileView(UserProfileMixin, View):

    show_web = False
    template_name = 'users/user_profile.html'
    
    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        business_id = None
        if self.show_web:
            business_handler = kwargs.get('business_handler')
            business = get_object_or_404(Account, handler=business_handler)
            business_id = business.id
        else:
            business_id = kwargs.get('business_id')
        custom_user = CustomUser.objects.get(user__id=user_id)     
        if not custom_user.profile_image:
            custom_user.profile_image_url = static('img/user_profile/placeholder.jpg')
        else:
            custom_user.profile_image_url = custom_user.profile_image.url

        context =  {'custom_user': custom_user}

        if business_id:
            business = Account.objects.get(pk=business_id)
            for image in business.photos.all():
                print(f'url: {image.image.url}')
            context['business'] = business

        if self.show_web:
            self.template_name = ['web/user_profile.html']

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        custom_user = CustomUser.objects.get(user__id=user_id)
        user = custom_user.user
        social_media = custom_user.social_media

        presentation = request.POST.get('presentation')
        experience = request.POST.get('experience')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        social_media.facebook = request.POST.get('facebook')
        social_media.twitter = request.POST.get('twitter')
        social_media.instagram = request.POST.get('instagram')
        social_media.tiktok = request.POST.get('tiktok')
        
        user.first_name = first_name
        user.last_name = last_name
        custom_user.presentation = presentation
        custom_user.experience = experience
        profile_image = request.FILES.get('profile_image')
        if profile_image:
            custom_user.profile_image.save(profile_image.name, profile_image)

        custom_user.save()
        social_media.save()
        user.save()
        return redirect('user_profile', user_id=user_id)

class ServiceView(TemplateView):
    template_name = 'web/service.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        event_handler = kwargs['event_handler']
        event = get_object_or_404(Event, handler=event_handler)
        business = event.account

        if not event.ui.image:
            event.ui.image_url = static('img/event/placeholder.jpg')
        else:
            event.ui.image_url = event.ui.image

        context.update({
            'event': event,
            'business': business,
        })

        return context
    
@user_is_event_admin
def load_more_images(request, event_id):
    count = int(request.GET.get('count', 9))
    images = BusinessEventImageUpload.objects.filter(event_id=event_id)[count:count+9]
    image_data = [{'url': img.image.url} for img in images]
    return JsonResponse({'data': image_data})

@user_owns_resource
def load_more_custom_user_images(request, custom_user_id):
    count = int(request.GET.get('count', 9))
    images = UserWorkImageUpload.objects.filter(user=custom_user_id)[count:count+9]
    image_data = [{'url': img.image.url} for img in images]
    return JsonResponse({'data': image_data})

@user_is_event_admin
def upload_event_photo(request, event_id):
    if request.method == 'POST': 
        event = Event.objects.get(pk=event_id)
        image_file = request.FILES.get('image')
        if image_file.size > 512000:
            return JsonResponse({'success': False, 'message' : 'File size exceeds 0.5MB. Please upload a smaller file.'})
        if image_file:
            new_image = BusinessEventImageUpload(account=event.account, event=event, image=image_file)
            new_image.save()
            return JsonResponse({'success': True, 'url': new_image.image.url, 'image_id': new_image.id})
        return JsonResponse({'success': False})
    
    return JsonResponse({'success': False})

@user_owns_resource
def upload_custom_user_photo(request, custom_user_id):
    if request.method == 'POST':
        custom_user = CustomUser.objects.get(pk=custom_user_id)
        image_file = request.FILES.get('image')
        if image_file.size > 512000:
            return JsonResponse({'success': False, 'message' : 'File size exceeds 0.5MB. Please upload a smaller file.'})
        if image_file:
            new_image = UserWorkImageUpload(user=custom_user, image=image_file)
            new_image.save()
            return JsonResponse({'success': True, 'url': new_image.image.url, 'image_id': new_image.id})
        return JsonResponse({'success': False})
    
    return JsonResponse({'success': False})

@require_POST
@user_is_event_admin
def delete_event_photos(request):
    try:
        # Load image IDs from POST request; assuming JSON body
        event_id = request.POST.get('event_id')
        image_ids = request.POST.get('image_ids')
        if image_ids:
            image_ids = json.loads(image_ids)

        # Query for the images
        images = BusinessEventImageUpload.objects.filter(id__in=image_ids)

        # Delete the files associated with the images
        for image in images:
            file_path = os.path.join(settings.MEDIA_ROOT, image.image.name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Delete the image records
        images.delete()

        return JsonResponse({'success': True, 'message': 'Images deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Failed to delete images.', 'error': str(e)})

@require_POST
@user_owns_resource
def delete_custom_user_photos(request):
    try:
        image_ids = request.POST.get('image_ids')
        if image_ids:
            image_ids = json.loads(image_ids)

        # Query for the images
        images = UserWorkImageUpload.objects.filter(id__in=image_ids)

        # Delete the files associated with the images
        for image in images:
            file_path = os.path.join(settings.MEDIA_ROOT, image.image.name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Delete the image records
        images.delete()

        return JsonResponse({'success': True, 'message': 'Images deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Failed to delete images.', 'error': str(e)})

class BusinessAppearanceView(BusinessAccessMixin, View):
    template_name = 'business/business_appearance.html'

    def get(self, request, *args, **kwargs):
        account_id = kwargs.get('business_id')
        business = get_object_or_404(Account, pk=account_id)
        appearance, created = BusinessAppearance.objects.get_or_create(account_id=account_id)

        if not appearance.appointment_background_image:
            appearance.appointment_background_image_url = static('img/appointment/placeholder.jpg')
        else:
            appearance.appointment_background_image_url = appearance.appointment_background_image.url

        form = BusinessAppearanceForm(instance=appearance)
        return render(request, self.template_name, {'form': form,
                                                    'business': business})

    def post(self, request, *args, **kwargs):
        account_id = kwargs.get('business_id')
        appearance, created = BusinessAppearance.objects.get_or_create(account_id=account_id)
        form = BusinessAppearanceForm(request.POST, request.FILES, instance=appearance)
        business = get_object_or_404(Account, pk=account_id)

        remove_background_image = request.POST.get('remove_background_image') == 'true'

        if 'appointment_background_image' in request.FILES:
            image_file = request.FILES['appointment_background_image']
            if image_file.size > 512000:  # 0.5MB in bytes
                form.add_error('appointment_background_image', 'File size exceeds 0.5MB. Please upload a smaller file.')                
        
        if form.is_valid():
            if remove_background_image:
                if appearance.appointment_background_image and appearance.appointment_background_image.url != 'appointment/placeholder.jpg':
                    appearance.appointment_background_image.delete(save=False)
                                    
                appearance.appointment_background_image = 'appointment/placeholder.jpg'
            form.save()
            return redirect('business_appearance', business_id = account_id)
        return render(request, self.template_name, {'form': form, 'business': business})
    
class BusinessConfigurationStatus:
    def __init__(self,business):
        self.business = business
        self.has_at_least_one_event = business.events.count() > 0
        self.has_at_least_one_business_hour = business.opening_hours.count() > 0
        self.has_at_least_sevent_business_hours = business.opening_hours.count() > 7
        self.has_business_presentation = business.presentation.strip() != ''
        self.has_header_image = False
        default_image_url = static('img/business/placeholder.jpg')
        if business.ui.header_image:
            self.has_header_image = business.ui.header_image.url != default_image_url        
        self.percentage_completed = self.has_at_least_one_event * 20 + self.has_at_least_one_business_hour  * 20 + \
                                    self.has_at_least_sevent_business_hours * 20 + self.has_business_presentation * 20 + \
                                    self.has_header_image * 20

    def get(self):
        return {
            'has_events': self.has_at_least_one_event,
            'has_business_hours': self.has_at_least_one_business_hour,
            'has_all_business_hours': self.has_at_least_sevent_business_hours,
            'has_business_presentation': self.has_business_presentation,
            'has_header_image': self.has_header_image,
            'percentage_completed': self.percentage_completed
        }
    
class EventConfigurationStatus:
    def __init__(self,event):
        self.event = event
        self.has_presentation = event.presentation.strip() != ''
        self.has_description = event.ui.description.strip() != ''
        self.has_duration = event.duration > 0
        self.has_workers = event.event_workers.count() > 0
        self.has_price = event.price >= 0
        self.has_front_image = False
        default_image_url = static('img/event/placeholder.jpg')
        if event.ui.image:
            self.has_front_image = event.ui.image.url != default_image_url 
        self.percentage_completed = self.has_duration * 20 + self.has_workers * 20 + self.has_presentation * 15 + \
                                    self.has_description * 15 + self.has_price * 15 + self.has_front_image * 15

    def to_dict(self):
        return {
            'has_presentation': self.has_presentation,
            'has_description': self.has_description,
            'has_duration': self.has_duration,
            'has_workers': self.has_workers,
            'has_price': self.has_price,
            'has_front_image': self.has_front_image,
            'percentage_completed': self.percentage_completed
        }

@require_POST
def send_business_invitation(request):
    recipient_email = request.POST.get('recipient_email')
    recipient_name = request.POST.get('recipient_name')
    notes = request.POST.get('notes')
    business_id = request.POST.get('business_id')
    business = Account.objects.get(id=business_id)

    invitation, created = AccountInvitation.objects.get_or_create(
        business=business,
        recipient_email=recipient_email,
        defaults={'recipient_name': recipient_name, 'notes': notes}
    )

    message = ''
    send_email = False
    if not created and not invitation.accepted:
        # Logic to resend the email if invitation not accepted
        message = 'Invitation resent.'
        send_email = True
    elif not created and invitation.accepted:
        message = 'User already accepted your invitation. Please, contact support if the user is not listed under your business'
    elif created:
        message = 'Invitation sent'
        send_email = True

    if send_email:
        # Prepare the token link
        confirmation_url = request.build_absolute_uri(
            reverse('confirm_business_invitation', args=[invitation.token])
        )

        subject = f"Invitation to join {business.name}"

        plain_message = f"""
        Hello {recipient_name},

        You have been invited to join {business.name} on OurApp.

        Please follow this link to accept the invitation: {confirmation_url}
        """

        html_message = f"""
            <p>Hello {recipient_name},</p>
            <p>You have been invited to join {business.name} on OurApp.</p>
            <p>Please <a href="{confirmation_url}">click here</a> to accept the invitation.</p>
        """

        send_mail(            
            subject=subject,
            message=plain_message,
            from_email= f"{business.name} via ReservaClick <{settings.EMAIL_HOST_USER}>",
            recipient_list=[recipient_email],
            html_message=html_message
        )        

    return JsonResponse({'message': message}, status=200)

def confirm_invitation(request, token):
    try:
        invitation = AccountInvitation.objects.get(token=token, accepted=False)
        if request.user.is_authenticated:
            if request.user.email == invitation.recipient_email:     
                custom_user = request.user.customuser  
                print('custom_user:' + custom_user.user.last_name)

                # Assign user to business
                business = invitation.business
                business.account_workers.add(custom_user) 

                # Set the invitation as accepted
                invitation.accepted = True
                invitation.accepted_on = timezone.now()
                invitation.save()

                # Redirect to a confirmation page or dashboard
                return redirect('dashboard')
            else:
                # If the logged-in user does not match the invitation email, log them out and ask to login with the correct account.
                try:
                    User = get_user_model()
                    user = User.objects.get(email=invitation.recipient_email)
                    return redirect(f'{reverse("logout")}?next={reverse("user_login")}&un={user.username}')
                except User.DoesNotExist:
                    # The client is logged in as a certain user but the invitation is for a different email so it will have to register
                    registration_url = f'{reverse("user_registration")}?email={invitation.recipient_email}&next={reverse("confirm_business_invitation", args=[token])}'
                    return redirect(registration_url)
        else:
            # Attempt to find the user by email to determine redirection
            try:
                User = get_user_model()
                user = User.objects.get(email=invitation.recipient_email)
                return redirect(f'{reverse("user_login")}?next={reverse("confirm_business_invitation", args=[token])}&un={user.username}')
            except User.DoesNotExist:
                # No user exists, redirect to registration
                registration_url = f'{reverse("user_registration")}?email={invitation.recipient_email}&next={reverse("confirm_business_invitation", args=[token])}'
                return redirect(registration_url)
    except AccountInvitation.DoesNotExist:
        return render(request, 'generic_error.html', {'message': 'Invalid or expired invitation.'})
    
def home(request):
    return render(request, 'home/home.html')

@login_required
def appointments(request):
    # Default values for the initial load
    start_date = timezone.now().date()
    end_date = timezone.now().date() + timezone.timedelta(days=30)
    user = request.user.customuser

    error_message = None
    initial_load = False

    if request.method == 'GET':
        # Check if the form has been submitted
        if 'start_date' in request.GET and 'end_date' in request.GET and 'user' in request.GET:
            form = AppointmentSearchForm(request=request, data=request.GET)
        else:
            # Use default values if the form is not submitted
            initial_load = True
            initial_data = {
                'start_date': start_date,
                'end_date': end_date,
                'user': user.id
            }
            form = AppointmentSearchForm(request=request, initial=initial_data)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            user = form.cleaned_data['user']

        if form.is_valid() or initial_load:
            if (end_date - start_date).days > 60:
                error_message = "Date range cannot exceed 60 days."
                appointments = defaultdict(list)
            else:
                print('Querying results')
                appointments_query = Appointment.objects.filter(
                    date__range=(start_date, end_date),
                    worker=user
                ).select_related('event', 'event__account').order_by('date', 'time')
                print(appointments_query)
                appointments = defaultdict(list)
                for appt in appointments_query:
                    appointments[appt.date].append(appt)

                print(f'appointments: {appointments}')
        else:
            print('Form not valid')
            appointments = defaultdict(list)
            error_message = "Invalid form data. Please check your input."

    context = {
        'form': form,
        'appointments': dict(appointments),
        'error_message': error_message,
    }
    return render(request, 'users/appointments.html', context)