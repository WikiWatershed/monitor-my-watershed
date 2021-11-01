from django.http import HttpResponse, HttpRequest
from django.shortcuts import render

APP_DIR = 'timeseries_visualization'

def home(request:HttpRequest) -> HttpResponse:
	return render(request, f'{APP_DIR}/tool.html')