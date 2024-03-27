from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404, HttpResponseBadRequest, HttpResponseNotFound
from .forms import AppointmentForm, SignUpForm, AppointmentCancelForm, CreateAccountForm, CreateEventForm, SelectWorkerForm, SelectEventForm, SelectDateTimeForm, CustomerInformationForm
from django.conf import settings
from django.core.mail import send_mail
from .models import Appointment, Event, Account, Invitee, CustomUser, OpenningTime, SpecialDay, WEEKDAYS
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.core import serializers
import json
from formtools.wizard.views import SessionWizardView
from datetime import datetime, timedelta
import time
from .libs.send_emails import gmail_send, gmail_compose, gmail_credentials
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from django.views.generic import View, DetailView
from django.contrib.auth.views import LoginView

class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_details.html'  
    context_object_name = 'event'

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True  # Redirect users who are already logged in
    next_page = reverse_lazy('dashboard')  # Redirect to dashboard after login

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add custom context here
        return context
    
class LoggedOutView(TemplateView):
    template_name = 'registration/logged_out.html'

class UserProfileView(TemplateView):
    template_name = 'users/profile.html'

class AccountListView(ListView):
    show_dropdown = False
    model = Account
    context_object_name = 'accounts'

    def get(self, request, *args, **kwargs):
        # Get the user's accounts
        user_accounts = self.get_queryset()
        # If only one account is assigned, redirect to that account's detail page
        if user_accounts.count() == 1 and self.show_dropdown:
            return redirect('appointment_wizard', business_id=user_accounts.first().pk) 
        
        # Otherwise, continue with the normal flow
        return super(AccountListView, self).get(request, *args, **kwargs)

    def get_template_names(self):
        if self.show_dropdown:
            return ['business/business_list_for_appointment.html']
        else:
            self.paginate_by = 10
            return ['business/business_list.html']

    def get_queryset(self):
        # Assuming you have a method to get the custom user
        user = CustomUser.objects.get(user=self.request.user)
        return Account.objects.filter(admins=user)

class SpecialDayView(View):
    def post(self, request, *args, **kwargs):
        
        date = request.POST.get('date')
        closed = request.POST.get('closed', False)
        from_hour = request.POST.get('from_hour')
        to_hour = request.POST.get('to_hour')
        account_id = request.POST.get('account_id')

        special_day_id = kwargs.get('id')

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

class BusinessHourView(View):
    def post(self, request, *args, **kwargs):

        hour_id = kwargs.get('id', None)
        weekday = request.POST.get('weekday')
        from_hour = request.POST.get('from_hour')
        to_hour = request.POST.get('to_hour')
        account_id = request.POST.get('account_id')

        print(f'hour_id: {hour_id}' )
        print(f'id: {hour_id}' )
        print(f'weekday: {weekday}' )
        print(f'from_hour: {from_hour}' )
        print(f'to_hour: {to_hour}' )
        print(f'account_id: {account_id}' )

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

class AppointmentCancelView(UpdateView):
    model = Appointment    
    template_name = "appointments/cancel_appointment.html"
    form_class = AppointmentCancelForm

class AppointmentView(View):
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
        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.status != 'CANCELLED':
            appointment.status = 'CANCELLED'
            appointment.save()
            response = {'status': 'success', 'message': 'Appointment cancelled successfully'}
        else:
            response = {'status': 'failed', 'message': 'Appointment already cancelled'}
        return JsonResponse(response)
    
class BusinessWorkerView(View):
    show_remove_button = False
    
    def get(self, request, *args, **kwargs):
        worker_id = kwargs.get('worker_id')
        account_id = kwargs.get('account_id')
        worker = get_object_or_404(CustomUser, id=worker_id)
        account = get_object_or_404(Account, id=account_id)
        if worker in account.account_workers.all():
            # Events the worker has assign for a particular business
            events = Event.objects.filter(account_id=account_id, event_workers__id=worker_id)
            # Appointments for that user for this business in the next 30 days
            today = datetime.today()
            end_date = today + timedelta(days=30)
            appointments = Appointment.objects.filter(worker_id = worker_id, event__account = account, date__gte = today, date__lte = end_date)
            # group appointments by date
            grouped_appointments = {}
            for appt in appointments:
                if appt.date in grouped_appointments:
                    grouped_appointments[appt.date].append(appt)
                else:
                    grouped_appointments[appt.date] = [appt]

            return render(request, 'worker_detail.html', {
                'worker': worker,
                'events': events,
                'appointments': grouped_appointments,
                'account_id': account_id,
                'show_remove_button': self.show_remove_button
            })
        else:
            raise Exception("Error: The worker is not assigned to the account")

    def post(self, request, *args, **kwargs):
        worker_id = self.kwargs['worker_id']
        account_id = self.kwargs['account_id'] 
        worker = get_object_or_404(CustomUser, id=worker_id)
        account = get_object_or_404(Account, id=account_id)
        if worker in account.account_workers.all():
            account.account_workers.remove(worker)
            # TODO: Remove the worker from the events for that business
            response = {'status': 'success', 'message': 'Worker removed successfully from your business'}
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
    while current_time <= end_time:
        # Add the current time to the list of slots
        slots.append(current_time)
        # Increment the current time by the duration
        current_time = addMins(current_time, duration)

    print(f'-------------------_> slots: {slots}')
    return slots

def build_available_time_slots(business_id, event_id, worker_id, date_str):

    # Get the business info
    account = Account.objects.get(id=business_id)
    time_slot_duration = account.time_slot_duration

    # Get the event duration
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    event = Event.objects.get(id=event_id)
    event_duration = event.duration

    # Get the account opening hours        
    opening_hours = OpenningTime.objects.get(account = business_id, weekday = str(date.weekday()))
    slots = generate_time_slots(opening_hours.from_hour, opening_hours.to_hour, time_slot_duration)

    # Get the appointments the worker has for the date
    appointments = Appointment.objects.filter(worker = worker_id, date=date).all().order_by('time')

    # Find the slots that are not available
    busy_time_slots = []
    for appointment in appointments:
        appt_start = appointment.time
        appt_end = addMins(appt_start, appointment.event.duration)
        print(':::::::::::::: appt start: ' + str(appt_start))
        print(':::::::::::::: appt end: ' + str(appt_end))

        for slot in slots:
            potential_appt_start = slot
            potential_appt_end = addMins(potential_appt_start, event_duration)
            if slot not in busy_time_slots and potential_appt_end > appt_start and potential_appt_start < appt_end:
                print(':::::::::::::: potential_appt_start: ' + str(potential_appt_start))
                print(':::::::::::::: potential_appt_end: ' + str(potential_appt_end))
                print('---------------> BUSY')
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

# Create your views here.
APPOINTMENT_STEP_FORMS = (
    ('Event', SelectEventForm),
    ('Worker', SelectWorkerForm),
    ('DateTime', SelectDateTimeForm),
    ('CustomerInfo', CustomerInformationForm)
)

class BookingCreateWizardView(SessionWizardView):
    template_name = "appointments/appointment_wizard.html"
    form_list = APPOINTMENT_STEP_FORMS    
    progress_width = 25
    initial_dict = { }

    def get_context_data(self, form, **kwargs):    
        print('-------------------- get_context_data')    
        context = super().get_context_data(form=form, **kwargs)
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

        context.update({
            "progress_width": self.progress_width,
            "booking_bg": 'booking_bg.jpg',
            "description": 'Select your Appt',
            "title": 'Big Appointment Title',
            "get_available_time" : time_list,
            "business_id" : business_id,
            "event_id" : event_id,
            "worker_id" : worker_id,
        })

        return context
    
    def get_form_initial(self, step):
        if step == 'Event':
            print('In get form initial - Event')
            business_id = self.kwargs['business_id']            
            self.initial_dict['Event'] = {'business_id': business_id}
        elif step == 'Worker': 
            print('In get form initial - Worker')
            if 'Event-events' in self.request.POST:
                print(f'Event-events: {self.request.POST.get("Event-events")}')
                self.initial_dict['Worker'] = {'event_id': self.request.POST.get('Event-events')} 
        elif step == 'DateTime':
            if 'Worker-workers' in self.request.POST:
                self.initial_dict['DateTime'] = {'worker_id': self.request.POST.get('Worker-workers')} 

        return self.initial_dict

    def render(self, form=None, **kwargs):    
        form = form or self.get_form()        
        
        if self.steps.current == 'Event':
            self.progress_width = 0
        elif self.steps.current == 'Worker':
            self.progress_width = 25    
        elif self.steps.current == 'DateTime':
            self.progress_width = 50    
        elif self.steps.current == 'CustomerInfo':
            self.progress_width = 75   
        
        context = self.get_context_data(form=form, **kwargs)    
        print('==========================')
        print(context)
        print('==========================')
        return self.render_to_response(context)
    
    def done(self, form_list, **kwargs):
        data = dict((key, value) for form in form_list for key,
                    value in form.cleaned_data.items())
        print(data)
        # Create the appointment
        invitee = Invitee(name = data['user_name'], email = data['user_email'], phone_number = data['user_mobile'])
        invitee.save()
        event = Event.objects.get(id = data['events'])
        custom_user = CustomUser.objects.get(id = data['workers'])
        appointment = Appointment(event = event, date = data['date'], time = data['time'], worker = custom_user, location='Default' )
        appointment.save()
        appointment.invitees.add(invitee)

        return render(self.request, 'appointments/appointment_done.html', {
            "progress_width": "100"
        })        
'''
def appointment(request, business_id, event_id):
    if request.method == 'POST':
        form = AppointmentForm(request.POST, business_id = business_id, event_id = event_id)
        if form.is_valid():
            print('++++++++++++++++++++++++++++++++')
            dt = form.cleaned_data['datetime']
            name = form.cleaned_data['user_name']
            email = form.cleaned_data['email']
            workers = form.cleaned_data['workers']
            print(workers[0])
            print('----------------------')
            print(f"user: {name} with email: {email} made an appointment for: {dt}")

            # Create the new appointment in the db
            event = Event.objects.get(id=event_id)
            worker = CustomUser.objects.get(id=workers[0])
            invitee = Invitee.objects.create(name = name, email = email)
            invitee.save()
            appt = Appointment(datetime = dt, event = event, worker = worker)
            appt.save()
            appt.invitees.add(invitee)
            
            # Send emails with smtp
            send_mail(
                subject='Your reservation with IMH Studio',
                message='Thanks for booking with IMH Studio, your appointment is on 12th May 2024',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=['farrones@yahoo.com']
            )
            
            # Testing send emails with OAuth2
            #mail_subject = "Test Email"
            #mail_body = "Hola nen!"
            #creds = gmail_credentials()
            #email_recipient = 'farrones@yahoo.com'
            #mail_content = gmail_compose(mail_subject, email_recipient, mail_body)
            #gmail_send(creds, mail_content)           
            

            return HttpResponse('Form successfully submitted') 

    elif request.method == 'GET':
        form = AppointmentForm(business_id = business_id, event_id = event_id)
        context = {'form': form}
        return render(request, 'appointment.html', context)
'''
class DashboardView(ListView):
    context_object_name = 'accounts'
    template_name = 'dashboard.html'

    def get_queryset(self):
        queryset = Account.objects.filter(admins__id= self.request.user.id)
        print('------------------------> queryset: ' + str(queryset))
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.today()
        end_date = today + timedelta(days=30)
        appointments = Appointment.objects.filter(worker__id = self.request.user.id, date__gte = today, date__lte = end_date).order_by('date')
        # group appointments by date
        grouped_appointments = {}
        for appt in appointments:
            if appt.date in grouped_appointments:
                grouped_appointments[appt.date].append(appt)
            else:
                grouped_appointments[appt.date] = [appt]
        context['appointments'] = grouped_appointments
        return context

def user_registration(request):
    if request.method == 'POST':  
        form = SignUpForm(request.POST)  
        
        if form.is_valid():  
            user = form.save()  
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect('dashboard/')
    else:  
        form = SignUpForm()
    context = {  
        'form':form  
    }  
    return render(request, 'registration/user_registration.html', context)     

def add_business(request):
    if request.method == 'POST':
        form = CreateAccountForm(request.POST)
        if form.is_valid():
            # Save the form to create an Account object but do not commit to the database yet
            new_account = form.save(commit=False)
            new_account.save()  # Save the new Account object to the database
            # Add the current user as an admin of the new account
            new_account.admins.add(CustomUser.objects.get(user=request.user))
            # If there are many-to-many fields included in the form, save the form with commit=True to save those relationships
            form.save_m2m()
            return redirect('business-list')
    else:
        form = CreateAccountForm()

    context = {'form': form}
    return render(request, 'business/add_business.html', context)

    
def view_business(request, business_id = -1):
    business = Account.objects.get(pk=business_id)
    business_hours = OpenningTime.objects.filter(account = business_id)
    special_days = SpecialDay.objects.filter(account = business_id)
    events = Event.objects.filter(account_id=business_id)

    for business_hour in business_hours:
        business_hour.to_hour = business_hour.to_hour.strftime('%H:%M')
        business_hour.from_hour = business_hour.from_hour.strftime('%H:%M')

    for special_day in special_days:
        special_day.to_hour = special_day.to_hour.strftime('%H:%M')
        special_day.from_hour = special_day.from_hour.strftime('%H:%M')
    
    context = {'business' : business,
               'business_hours' : business_hours,
               'special_days' : special_days,
               'events' : events,
               'available_days': WEEKDAYS}
               
    return render(request, 'business/view_business.html', context) 

def add_business_event(request, business_id = -1):
    if request.method == 'POST':
        form = CreateEventForm(request.POST)
        if form.is_valid():
            new_event = form.save(commit=False)
            business = Account.objects.get(pk=business_id)
            new_event.account = business
            new_event.save()
            form.save_m2m()
            return redirect('view_business', business_id = business_id)
        
    elif request.method == 'GET':
        form = CreateEventForm()
        context = {
            'form': form,
            'business_id': business_id}
        return render(request, 'add_business_event.html', context)
