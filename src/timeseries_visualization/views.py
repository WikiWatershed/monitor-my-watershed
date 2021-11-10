from django.http import HttpResponse, HttpRequest
from django.shortcuts import render

APP_DIR = 'timeseries_visualization'

def tsv(request:HttpRequest, sampling_feature_code:str='') -> HttpResponse:
	args = {}
	args['sampling_feature_code'] = sampling_feature_code
	return render(request, f'{APP_DIR}/tool.html', args)