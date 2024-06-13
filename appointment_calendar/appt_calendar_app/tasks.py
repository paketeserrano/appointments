from django.core.mail import send_mail
from django.conf import settings
from django_q.tasks import async_task

def send_email(subject, from_email, plain_message, recipient_email, html_message):
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=from_email,
        recipient_list=recipient_email,
        html_message=html_message
    )

def send_email_with_retries(subject, from_email, plain_message, recipient_email, html_message):
    async_task(
        'appt_calendar_app.tasks.send_email_wrapper',
        subject,
        from_email,
        plain_message,
        recipient_email,
        html_message,
        hook='appt_calendar_app.tasks.retry_hook',
    )

def send_email_wrapper(subject, from_email, plain_message, recipient_email, html_message):
    recipient_list = [recipient_email] if isinstance(recipient_email, str) else recipient_email
    send_email(subject, from_email, plain_message, recipient_email, html_message)

def retry_hook(task):   
    if not task.success:
        # Log the failure with the exception
        print(f"Sending email task {task.id} failed after {task.attempt_count} attempts")
        if task.result:
            print(f"Exception: {task.result}")
    else:
        # Log the success
        print(f"Task {task.id} succeeded")
