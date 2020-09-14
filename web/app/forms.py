from django.conf import settings
import logging
import requests
from django.db import models
from django.forms import ModelForm, Form, CharField, ChoiceField, Textarea, HiddenInput, BooleanField, ValidationError
from allauth.account.forms import SignupForm
import phonenumbers
from pushbullet import Pushbullet, PushbulletError

from .widgets import CustomRadioSelectWidget, PhoneCountryCodeWidget
from .models import *

LOGGER = logging.getLogger(__name__)

class PrinterForm(ModelForm):
    class Meta:
        model = Printer
        fields = ['name', 'action_on_failure', 'tools_off_on_pause', 'bed_off_on_pause',
                  'detective_sensitivity', 'retract_on_pause', 'lift_z_on_pause']
        widgets = {
            'action_on_failure': CustomRadioSelectWidget(choices=Printer.ACTION_ON_FAILURE),
        }


class UserPreferencesForm(ModelForm):
    telegram_chat_id = CharField(widget=HiddenInput(), required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_country_code', 'phone_number', 'pushbullet_access_token',
                  'telegram_chat_id', 'notify_on_done', 'notify_on_canceled', 'account_notification_by_email',
                  'print_notification_by_email', 'print_notification_by_pushbullet', 'print_notification_by_telegram',
                  'alert_by_sms', 'alert_by_email', 'discord_webhook', 'print_notification_by_discord']
        widgets = {
            'phone_country_code': PhoneCountryCodeWidget()
        }

    def clean_phone_country_code(self):
        phone_country_code = self.cleaned_data['phone_country_code']
        if phone_country_code and not phone_country_code.startswith('+'):
            phone_country_code = '+' + phone_country_code
        return phone_country_code

    def clean(self):
        data = self.cleaned_data

        phone_number = (data['phone_country_code'] or '') + \
            (data['phone_number'] or '')

        if data['phone_country_code'] and data['phone_number']:
            phone_number = data['phone_country_code'] + data['phone_number']
            try:
                phone_number = phonenumbers.parse(phone_number, None)
                if not phonenumbers.is_valid_number(phone_number):
                    self.add_error('phone_number', 'Invalid phone number')
            except phonenumbers.NumberParseException as e:
                self.add_error('phone_number', e)

        if data['pushbullet_access_token']:
            pushbullet_access_token = data['pushbullet_access_token']
            try:
                Pushbullet(pushbullet_access_token)
            except PushbulletError:
                self.add_error('pushbullet_access_token',
                               'Invalid pushbullet access token.')

        data['telegram_chat_id'] = data['telegram_chat_id'] if data['telegram_chat_id'] else None


class RecaptchaSignupForm(SignupForm):
    recaptcha_token = CharField(required=True)

    def clean(self):
        super().clean()

        # captcha verification
        data = {
            'response': self.cleaned_data['recaptcha_token'],
            'secret': settings.RECAPTCHA_SECRET_KEY
        }
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)

        if response.status_code == requests.codes.ok:
            if response.json()['success'] and response.json()['action'] == 'signup_form':
                LOGGER.debug('Captcha valid for user={}'.format(self.cleaned_data.get('email')))
            else:
                LOGGER.warn('Captcha invalid for user={}'.format(self.cleaned_data.get('email')))
                raise ValidationError('ReCAPTCHA is invalid.')
        else:
            LOGGER.error('Cannot validate reCAPTCHA for user={}'.format(self.cleaned_data.get('email')))

        return self.cleaned_data
