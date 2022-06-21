from __future__ import print_function
from .exceptions import MpesaConfigurationException, IllegalPhoneNumberException, MpesaConnectionError, MpesaError
from main.models import AccessToken
import requests
from django.utils import timezone
from decouple import config, UndefinedValueError
from requests import Response
import time
import os
from django.conf import settings
import base64
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15


class MpesaResponse(Response):
    response_description = ""
    error_code = None
    error_message = ''


def mpesa_response(r):
    r.__class__ = MpesaResponse
    json_response = r.json()
    r.response_description = json_response.get('ResponseDescription', '')
    r.error_code = json_response.get('errorCode')
    r.error_message = json_response.get('errorMessage', '')
    return r


def mpesa_config(key):
    
    value = getattr(settings, key, None)
    if value is None:
        try:
            value = config(key)
        except UndefinedValueError:
            # Check key in settings file
            raise MpesaConfigurationException('Mpesa environment not configured properly - ' + key + ' not found')

    return value


def api_base_url():

    mpesa_environment = mpesa_config('MPESA_ENVIRONMENT')

    if mpesa_environment == 'sandbox':
        return 'https://sandbox.safaricom.co.ke/'
    elif mpesa_environment == 'production':
        return 'https://api.safaricom.co.ke/'
    else:
        raise MpesaConfigurationException(
            'Mpesa environment not configured properly - MPESA_ENVIRONMENT should be sandbox or production')


def generate_access_token_request(consumer_key=None, consumer_secret=None):

    url = api_base_url() + 'oauth/v1/generate?grant_type=client_credentials'
    consumer_key = consumer_key if consumer_key is not None else mpesa_config('MPESA_CONSUMER_KEY')
    consumer_secret = consumer_secret if consumer_secret is not None else mpesa_config('MPESA_CONSUMER_SECRET')

    try:
        r = requests.get(url, auth=(consumer_key, consumer_secret))
    except requests.exceptions.ConnectionError:
        raise MpesaConnectionError('Connection failed')
    except Exception as ex:
        return ex.message

    return r


def generate_access_token():


    r = generate_access_token_request()
    if r.status_code != 200:
        # Retry to generate access token
        r = generate_access_token_request()
        if r.status_code != 200:
            raise MpesaError('Unable to generate access token')

    token = r.json()['access_token']

    AccessToken.objects.all().delete()
    access_token = AccessToken.objects.create(token=token)

    return access_token


def mpesa_access_token():

    access_token = AccessToken.objects.first()
    if access_token is None:
        access_token = generate_access_token()
    else:
        delta = timezone.now() - access_token.created_at
        minutes = (delta.total_seconds() // 60) % 60
        print('minutes: ', minutes)
        if minutes > 30:
            # Access token expired
            access_token = generate_access_token()

    return access_token.token


def format_phone_number(phone_number):

    if len(phone_number) < 9:
        raise IllegalPhoneNumberException('Phone number too short')
    else:
        return '254' + phone_number[-9:]


def sleep(seconds, message=''):
    print()
    print('===')
    print(message, end="")
    for i in range(seconds * 2):
        time.sleep(0.5)
        print('.', end="")
    print()
    print('===')
    print()


def encrypt_security_credential(credential):
    mpesa_environment = mpesa_config('MPESA_ENVIRONMENT')

    if mpesa_environment in ('sandbox', 'production'):
        certificate_name = mpesa_environment + '.cer'
    else:
        raise MpesaConfigurationException(
            'Mpesa environment not configured properly - MPESA_ENVIRONMENT should be sandbox or production')

    certificate_path = os.path.join(settings.BASE_DIR, 'certs', certificate_name)
    return encrypt_rsa(certificate_path, credential)


def encrypt_rsa(certificate_path, input):
    message = input.encode('ascii')
    with open(certificate_path, "rb") as cert_file:
        cert = x509.load_pem_x509_certificate(cert_file.read())
        encrypted = cert.public_key().encrypt(message, PKCS1v15())
        output = base64.b64encode(encrypted).decode('ascii')

    return output