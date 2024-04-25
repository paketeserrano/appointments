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
from django.urls import reverse_lazy, reverse
from django.contrib.sites.shortcuts import get_current_site
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from django.views.generic import View, DetailView
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.views.decorators.http import require_POST

class EventDetailView(View):

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        return render(request, 'events/event_details.html', {'event': event})

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        
        # Update event fields with data from request
        event.name = request.POST.get('name', event.name)
        event.description = request.POST.get('description', event.description)
        event.duration = request.POST.get('duration', event.duration)
        event.location = request.POST.get('location', event.location)
        workerIds = json.loads(request.POST.get('worker_ids'))
        
        print('--------------------------')
        print(request.POST.get('worker_ids'))
        print('--------------------------')
        workers = CustomUser.objects.filter(pk__in=workerIds)
        event.event_workers.set(workers)

        event.save()
        return JsonResponse({'message': 'Event updated successfully'}, status=200)

    def delete(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        event.delete()
        return JsonResponse({'message': 'Event deleted successfully'}, status=204)


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

            # Current Custom User
            current_user = CustomUser.objects.get(user=self.request.user)

            # NOTE: Domain to build the links to the events. Use full_event_url if domain doesn't work in production
            domain = get_current_site(self.request).domain
            full_event_url = self.request.build_absolute_uri(domain)            

            return render(request, 'worker_detail.html', {
                'worker': worker,
                'events': events,
                'appointments': grouped_appointments,
                'account_id': account_id,
                'show_remove_button': self.show_remove_button,
                'current_user' : current_user,
                'domain' : domain
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
    client_appointment = False

    def get_context_data(self, form, **kwargs):    
        print('-------------------- get_context_data')    
        context = super().get_context_data(form=form, **kwargs)
        # This is the base template of the appointment_wizard. If it is the client making the appointment we will change this base
        base_template = 'appointments/base.html'
        if self.client_appointment:
            base_template = 'appointments/base_client_appointment.html'
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

        appointment_description = 'Select your Appt'
        if event_id:
            event = Event.objects.get(id=event_id)
            appointment_description = event.name

        context.update({
            "progress_width": self.progress_width,
            "booking_bg": 'booking_bg.jpg',
            "description": appointment_description,
            "title": business.name,
            "get_available_time" : time_list,
            "business_id" : business_id,
            "event_id" : event_id,
            "worker_id" : worker_id,
            "client_appointment" : self.client_appointment,
            "base_template" : base_template,
        })

        return context
    
    def get_form_initial(self, step):
        # Determine the type of Wizard.
        # Only business_id info -> Complete wizard: Select Event, Worker, Time and User Info
        # business_id and event_id -> Select Worker, Time and Info
        # business_id, event_id and worker_id selected -> Select Time and Info
        business_id = self.kwargs['business_id']

        event_id = None
        if 'event_id' in self.kwargs:
            event_id = self.kwargs['event_id']

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

        event_id = None
        if 'event_id' in self.kwargs:
            event_id = self.kwargs['event_id']
        else:
            event_id = data['events']

        worker_id = None
        if 'worker_id' in self.kwargs:
            worker_id = self.kwargs['worker_id']
        else:
            worker_id = data['workers']

        # Create the appointment
        invitee = Invitee(name = data['user_name'], email = data['user_email'], phone_number = data['user_mobile'])
        invitee.save()
        event = Event.objects.get(id = event_id)
        custom_user = CustomUser.objects.get(id = worker_id)
        appointment = Appointment(event = event, date = data['date'], time = data['time'], worker = custom_user, location='Default' )
        appointment.save()
        appointment.invitees.add(invitee)

        # Send confirmation email
        subject = 'Your appointment with ' + event.account.name + ' | ' + event.name
        message = 'Your appointment ' + event.name + ' at ' + event.account.name + ' with ' + appointment.worker.user.first_name + ' ' + \
                   appointment.worker.user.last_name + ' is on ' + appointment.date.strftime('%d-%m-%Y') +' at ' + appointment.time.strftime('%H:%M:%S')  + ' .'
        
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
                <h2>Thank You and Congratulations!</h2>
                <p>We are pleased to confirm your appointment. Here are the details:</p>
                <div class="details-card">
                    <p class="appointment-details">Your appointment: <span class="highlight">{event.name}</span></p>
                    <p class="appointment-details">Location: <span class="highlight">{event.account.name}</span></p>
                    <p class="appointment-details">With: <span class="highlight">{appointment.worker.user.first_name} {appointment.worker.user.last_name}</span></p>
                    <p class="appointment-details">Date: <span class="highlight">{appointment.date.strftime('%d-%m-%Y')}</span></p>
                    <p class="appointment-details">Time: <span class="highlight">{appointment.time.strftime('%H:%M:%S')}</span></p>
                </div>
                <p class="cancel-text">Do you need to cancel this appointment?</p>
                <a href="http://example.com/cancel_appointment/{appointment.id}" class="button">Cancel Appointment</a>
            </div>
        </body>
        </html>
        """

        send_mail(            
            subject=subject,
            message=message,
            from_email= f"{event.account.name} via ReservaClick <{settings.EMAIL_HOST_USER}>",
            recipient_list=['farrones@yahoo.com'],
            html_message=html_message
        )

        return render(self.request, 'appointments/appointment_done.html', {
            "progress_width": "100",
            "event" : event,
            "appointment" : appointment,
            "invitee" : invitee,
            "description": event.name,
            "title": event.account.name
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
            event__event_workers=current_user
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
    
@require_POST
def toggle_event_active(request):
    event_id = request.POST.get('event_id')
    event = get_object_or_404(Event, id=event_id)
    event.active = not event.active
    event.save()
    return JsonResponse({'status': 'success', 'event_active': event.active})
