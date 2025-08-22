from django.http import HttpResponse


def healthz(request):
    return HttpResponse("OK")


def home(request):
    return HttpResponse("EditEngine API - Deployment Successful")