from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, Http404
from .forms import AppointmentForm, SignUpForm, CreateAccountForm, CreateEventForm, SelectWorkerForm, SelectEventForm, SelectDateTimeForm, CustomerInformationForm
from django.conf import settings
from django.core.mail import send_mail
from .models import Appointment, Event, Account, Invitee, CustomUser, OpenningTime, SpecialDay
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.core import serializers
import json
from formtools.wizard.views import SessionWizardView
from datetime import datetime, timedelta
import time
from .libs.send_emails import gmail_send, gmail_compose, gmail_credentials
#####################################################################
##    CBV Testing
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView

class HomePageView(TemplateView):
    template_name = "test.html"



#####################################################################




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
            '''
            # Testing send emails with OAuth2
            mail_subject = "Test Email"
            mail_body = "Hola nen!"
            creds = gmail_credentials()
            email_recipient = 'farrones@yahoo.com'
            mail_content = gmail_compose(mail_subject, email_recipient, mail_body)
            gmail_send(creds, mail_content)           
            '''

            return HttpResponse('Form successfully submitted') 

    elif request.method == 'GET':
        form = AppointmentForm(business_id = business_id, event_id = event_id)
        context = {'form': form}
        return render(request, 'appointment.html', context)

class DashboardView(ListView):
    context_object_name = 'accounts'
    template_name = 'dashboard.html'

    def get_queryset(self):
        queryset = Account.objects.filter(admins__id= self.request.user.id)
        print('------------------------> queryset: ' + str(queryset))
        return queryset

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
            form.save()
            return redirect('/')
        pass
    elif request.method == 'GET':
        form = CreateAccountForm()
        context = {'form': form}
        return render(request, 'business/add_business.html', context)
    
def view_business(request, business_id = -1):
    business = Account.objects.filter(pk=business_id).values()
    business_hours = OpenningTime.objects.filter(account = business_id).values()
    special_days = SpecialDay.objects.filter(account = business_id).values()

    context = {'business' : business,
               'business_hours' : business_hours,
               'special_days' : special_days}
    return render(request, 'business/view_business.html', context) 

def add_business_event(request, business_id = -1):
    if request.method == 'POST':
        form = CreateEventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/view_business/' + str(business_id))
        
    elif request.method == 'GET':
        form = CreateEventForm()
        context = {
            'form': form,
            'business_id': business_id}
        return render(request, 'add_business_event.html', context)
