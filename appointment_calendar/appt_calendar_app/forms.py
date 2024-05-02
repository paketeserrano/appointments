from django import forms
from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm  
from django.core.exceptions import ValidationError  
from django.forms.fields import EmailField  
from django.forms.forms import Form 
from .models import Account, Event, Appointment, Invitee, Address
import json


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'

class ChangeInputsStyle(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add common css classes to all widgets
        for field in iter(self.fields):
            # get current classes from Meta
            input_type = self.fields[field].widget.input_type
            classes = self.fields[field].widget.attrs.get("class")
            if classes is not None:
                classes += " form-check-input" if input_type == "checkbox" else " form-control  flatpickr-input"
            else:
                classes = " form-check-input" if input_type == "checkbox" else " form-control flatpickr-input"
            self.fields[field].widget.attrs.update({
                'class': classes
            })
            
class SelectEventForm(ChangeInputsStyle):
    events = forms.ChoiceField(choices=[('1', '30m consultation'), ('2', '1h consultation')], required=True)

    def __init__(self,*args,**kwargs):
        super(SelectEventForm,self).__init__(*args,**kwargs)
        self.fields['events'] = forms.ChoiceField(choices=self.create_choices(self.initial['Event']['business_id']), required=True, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))   

    def create_choices(self, business_id):
        events = Event.objects.filter(account=business_id).all()
        event_choices = []
        for event in events:
            event_choices.append((str(event.id), event.name))
        return event_choices

class SelectWorkerForm(ChangeInputsStyle):
    workers = forms.ChoiceField(choices=[], label='Select Personnel')

    def __init__(self,*args,**kwargs):
        super(SelectWorkerForm,self).__init__(*args,**kwargs)
        self.fields['workers'] = forms.ChoiceField(choices=self.create_choices(self.initial['Worker']['event_id']), required=True, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))


    def create_choices(self, event_id):
        event = Event.objects.get(id=event_id)
        workers = event.event_workers.all()
        worker_choices = []
        for worker in workers:
            print(f'worker: {worker.user.first_name}')
            worker_choices.append((worker.user.id, worker.user.first_name))
            
        return worker_choices
        
class SelectDateTimeForm(ChangeInputsStyle):
    date = forms.DateField(required=True)
    time = forms.TimeField(widget=forms.HiddenInput())

class CustomerInformationForm(ChangeInputsStyle):
    user_name = forms.CharField(max_length=250)
    user_email = forms.EmailField()
    user_mobile = forms.CharField(required=False, max_length=10)

class AppointmentForm(forms.Form):
    def __init__(self,*args,**kwargs):
        self.event_id = kwargs.pop('event_id')
        self.business_id = kwargs.pop('business_id')
        super(AppointmentForm,self).__init__(*args,**kwargs)
        self.fields['workers'] = forms.ChoiceField(choices=self.create_worker_options(self.event_id), label= 'Select Worker')

    def create_worker_options(self, event_id):
        print(event_id)
        event = Event.objects.filter(pk=event_id).first()
        workers = event.event_workers.all()
        worker_choices = []
        for worker in workers:
            worker_choices.append((worker.id, worker.user.first_name + ' ' + worker.user.last_name))
            
        print(worker_choices)
        return worker_choices
    


    account = forms.CharField(label='Account', initial="IMH Studio", max_length = 120)
    event = forms.CharField(label='Event', initial='Free hair extensions consultation', max_length = 120)
    workers = forms.ChoiceField(choices=[], label= 'Select Worker')
    datetime = forms.DateTimeField(widget = DateTimeInput())
    email = forms.EmailField(label='Email', max_length = 254)
    user_name = forms.CharField(label='Name', max_length='120') 

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['address', 'city', 'province', 'country']
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CreateAccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'description', 'account_workers']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'account_workers': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class CreateEventForm(forms.ModelForm):
    class Meta:
        model = Event 
        fields = ['name', 'description', 'duration', 'event_workers'] 

class AppointmentCancelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AppointmentCancelForm, self).__init__(*args, **kwargs)

        # Only show the invitees for this appointment
        appointment = kwargs['instance']
        self.fields['invitees'].queryset = Invitee.objects.filter(appointment = appointment)

    class Meta:
        model = Appointment
        fields = ('event', 'date', 'time', 'invitees')
        widgets = {
            'event': forms.Select(attrs={"disabled":"disabled"}),
            'invitees': forms.SelectMultiple(attrs={"disabled":"disabled"}),
            'date': forms.TextInput(attrs={"disabled":"disabled"}),
            'time': forms.TextInput(attrs={"disabled":"disabled"})
        }