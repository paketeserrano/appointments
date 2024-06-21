from django import forms
from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm  
from django.core.exceptions import ValidationError  
from django.forms.fields import EmailField  
from django.forms.forms import Form 
from .models import Account, Event, Appointment, Invitee, Address, BusinessAppearance, EventPageAnswer, EventPageQuestion, CustomUser
import json
from django.utils import timezone

class EventQuestionForm(forms.ModelForm):
    class Meta:
        model = EventPageQuestion
        fields = ['text', 'required', 'active']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class EventAnswerForm(forms.ModelForm):
    class Meta:
        model = EventPageAnswer
        fields = ['answer_type', 'options']

        widgets = {
            'answer_type': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('single_line', 'Single Line'),
                ('multi_line', 'Multi Line'),
                ('checkbox', 'Checkbox'),
                ('radio', 'Radio Button'),
                ('dropdown', 'Dropdown')
            ]),
            'options': forms.Textarea(attrs={'class': 'form-control', 'style': 'display:none;'})
        }

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
        events = Event.objects.filter(account=business_id, active=True).all()
        event_choices = []
        for event in events:
            event_choices.append((str(event.id), event.name))
        return event_choices

class SelectWorkerForm(ChangeInputsStyle):
    workers = forms.ChoiceField(choices=[], label='Select Personnel')

    def __init__(self,*args,**kwargs):
        super(SelectWorkerForm,self).__init__(*args,**kwargs)
        self.fields['workers'] = forms.ChoiceField(choices=self.create_choices(self.initial['Worker']['event_id']), 
                                                   required=True, 
                                                   widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'style': 'padding-top: 1.5rem;'}))


    def create_choices(self, event_id):
        event = Event.objects.get(id=event_id)
        workers = event.event_workers.all()
        worker_choices = []
        for worker in workers:
            print(f'worker: {worker.user.first_name}')
            worker_choices.append((worker.user.id, worker.user.first_name))
            
        return worker_choices
        
class InactiveEventForm(ChangeInputsStyle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['info'] = forms.CharField(widget=forms.HiddenInput(), required=False, initial="This event is currently not available.")

class SelectDateTimeForm(ChangeInputsStyle):
    location = forms.ChoiceField(required=True, choices=[])
    date = forms.DateField(required=True)
    time = forms.TimeField(widget=forms.HiddenInput())    
    
    def __init__(self, *args, **kwargs):        
        event = kwargs.pop('event', None)
        location_choices = []        
        super(SelectDateTimeForm, self).__init__(*args, **kwargs)        

        if event:
            location_choices = [(location.id, str(location)) for location in event.locations.all()]
            if event.video_conference:
                location_choices.append(('video_conference', 'Video Conference'))

            # If the event has no locations, try to use the business address
            # Otherwise just choose the business name
            if not location_choices:
                if event.account.address:
                    location_choices.append((event.account.address.id, str(event.account.address)))
                else:
                    location_choices.append((event.account.name, event.account.name))
                                        
            self.fields['location'].choices = location_choices

        # Ensure the date field retains its attributes
        # For some reason the html id for this element is not kept when calling super(). I think it is because
        # super creates different id names
        self.fields['date'].widget.attrs.update({'id': 'id_DateTime-date'}) 
        self.fields['time'].widget.attrs.update({'id': 'id_DateTime-time'})
    
class CustomerInformationForm(ChangeInputsStyle):
    user_name = forms.CharField(max_length=250, widget=forms.TextInput(attrs={'class': 'form-control'}))
    user_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    user_mobile = forms.CharField(required=False, max_length=10, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        event = kwargs.pop('event', None)
        super(CustomerInformationForm, self).__init__(*args, **kwargs)
        print('Inside the Customer Info Form Constructor')
        if event:
            print('Inside the form questions part')
            questions = EventPageQuestion.objects.filter(event_page_options__event=event, active=True)
            for question in questions:
                print(f'question: {question.text}')
                field_name = f'question_{question.id}'
                field_label = question.text
                answer_type = question.answers.first().answer_type

                if question.required:
                    required = True
                else:
                    required = False

                # Determine the field type based on the answer type
                if answer_type == 'single_line':
                    self.fields[field_name] = forms.CharField(label=field_label, required=required, widget=forms.TextInput(attrs={'class': 'form-control'}))
                elif answer_type == 'multi_line':
                    self.fields[field_name] = forms.CharField(label=field_label, required=required, widget=forms.Textarea(attrs={'class': 'form-control'}))
                elif answer_type == 'checkbox':                  
                    options = question.answers.first().options
                    options = json.loads((json.loads(options)[0]))              
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label=field_label, 
                        required=required, 
                        widget=forms.CheckboxSelectMultiple(), 
                        choices=[(opt, opt) for opt in options])
                elif answer_type == 'radio':                
                    options = question.answers.first().options
                    # Done like this because of how we are saving the options
                    options = json.loads((json.loads(options)[0]))                     
                    self.fields[field_name] = forms.ChoiceField(
                        label=field_label, 
                        required=required, 
                        widget=forms.RadioSelect(), 
                        choices=[(opt, opt) for opt in options])
                elif answer_type == 'dropdown':                   
                    options = question.answers.first().options
                    options = json.loads((json.loads(options)[0]))                   
                    self.fields[field_name] = forms.ChoiceField(
                        label=field_label, 
                        required=required, 
                        widget=forms.Select(attrs={'class': 'form-control'}), 
                        choices=[(opt, opt) for opt in options])

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

class InviteeSearchForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(), 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    name = forms.CharField(
        max_length=120, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter name'}))
    
    email = forms.EmailField(
        max_length=240, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}))
    
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            accounts = Account.objects.filter(admins=user.customuser)
            self.fields['account'].queryset = accounts
            if accounts.count() > 1:
                self.fields['account'].empty_label = "All"
            else:
                self.fields['account'].empty_label = None 

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
        fields = ['name', 'presentation']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'presentation': forms.Textarea(attrs={'class': 'form-control', 'rows':'3'}),
            'account_workers': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class CreateEventForm(forms.ModelForm):
    class Meta:
        model = Event 
        fields = ['name', 'presentation', 'price','duration', 'event_workers'] 

    presentation = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 200}))

    def __init__(self, *args, **kwargs):
        account_id = kwargs.pop('account_id', None)
        super(CreateEventForm, self).__init__(*args, **kwargs)
        if account_id:
            business = Account.objects.get(pk=account_id)
            self.fields['event_workers'].queryset = business.account_workers.all()

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

class BusinessAppearanceForm(forms.ModelForm):
    class Meta:
        model = BusinessAppearance
        fields = ('header_bar_color', 'background_color', 'text_color', 'section_header_font_color', \
                  'service_background_color', 'worker_background_color', 'hero_image_font_color','header_bar_font_color', \
                  'main_manu_background_color', 'main_menu_font_color', 'main_menu_font_hover_color',\
                  'burger_button_background_color', 'buger_menu_lines_color', 'appointment_background_image', 'booking_form_background_color') 
        widgets = {
            'header_bar_color': forms.TextInput(attrs={'type': 'color'}),
            'background_color': forms.TextInput(attrs={'type': 'color'}),
            'text_color': forms.TextInput(attrs={'type': 'color'}),
            'section_header_font_color': forms.TextInput(attrs={'type': 'color'}),
            'service_background_color': forms.TextInput(attrs={'type': 'color'}),
            'worker_background_color': forms.TextInput(attrs={'type': 'color'}),
            'hero_image_font_color': forms.TextInput(attrs={'type': 'color'}),
            'header_bar_font_color': forms.TextInput(attrs={'type': 'color'}),
            'main_manu_background_color': forms.TextInput(attrs={'type': 'color'}),
            'main_menu_font_color': forms.TextInput(attrs={'type': 'color'}),
            'main_menu_font_hover_color': forms.TextInput(attrs={'type': 'color'}),
            'burger_button_background_color': forms.TextInput(attrs={'type': 'color'}),
            'buger_menu_lines_color': forms.TextInput(attrs={'type': 'color'}),
            'booking_form_background_color': forms.TextInput(attrs={'type': 'color'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Validation for each field to ensure it starts with '#' and is 7 characters long
        for field in self.fields:
            if field != 'appointment_background_image':
                if field in cleaned_data and not (cleaned_data[field].startswith('#') and len(cleaned_data[field]) == 7):
                    raise forms.ValidationError(f"{field.replace('_', ' ').capitalize()} must be a valid hex code.")
        return cleaned_data
    
class AppointmentSearchForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date()
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date() + timezone.timedelta(days=30)
    )
    user = forms.ModelChoiceField(queryset=CustomUser.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(AppointmentSearchForm, self).__init__(*args, **kwargs)
        if request:
            user = request.user.customuser
            user_ids = set()

            # Get all account workers and admins where the user is an admin
            for account in Account.objects.filter(admins=user):
                user_ids.update(account.account_workers.values_list('id', flat=True))
                user_ids.update(account.admins.values_list('id', flat=True))

            # Include the user itself if they are a worker in some accounts where they are not an admin
            for account in Account.objects.filter(account_workers=user):
                user_ids.add(user.id)

            # Get distinct CustomUser objects
            users = CustomUser.objects.filter(id__in=user_ids).distinct()
            self.fields['user'].queryset = users
            self.fields['user'].initial = user