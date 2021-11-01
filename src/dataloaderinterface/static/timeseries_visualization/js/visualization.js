var _chart;

var _axes = [];
var _plottedTimeseries = {};
var _resultMetadata = {};

// PRT - these are hardcoded for testing remove before production
var _samplingfeaturecode = 'WCC019';
//var _samplingfeaturecode = 'CWS-ThomasDairy2';

$(function () {
	initChart('cht_ts');

	getSamplingFeatureMetadata('CWS-ThomasDairy2');

	$(document).on('click', '.plottable-series', function() {
		resultid = $(this).attr('id').split("_")[1];
		checked = $(this).prop('checked');
		changeTimeSeries(resultid, checked);
	});

});

function changeTimeSeries(result_id, checked) {
	$plotted = $('#plottedSeries');
	$notplotted = $('#plottableSeries');
	$panel = $(`#series-panel_${result_id}`)
	if (checked) {
		getTimeseriesData(result_id, new Date('2000/10/01'), new Date('2021/10/28'));
		$panel.remove();
		$plotted.append($panel);
	}
	if (!checked) { 
		unPlotSeries(result_id);
		$panel.remove();
		$notplotted.append($panel);
	}
}

function initAddSeries(response) {
	response_obj = JSON.parse(response);
	for ([index, metadata] of Object.entries(response_obj)) {
		_resultMetadata[metadata.resultid] = metadata
	}	
	populateSeriesBlock();
}

function populateSeriesBlock(){
	$block = $('#plottableSeries')
	$block.empty();
	for ([key, metadata] of Object.entries(_resultMetadata)) {
		$panel = makeSeriesPanel(metadata);
		$block.append($panel);
	}	
}

function makeSeriesPanel(metadata) {
	zlocation_text = ''
	if (metadata.zlocation !== undefined) {
		zlocation_text = `: ${metadata.zlocation} ${metadata.zlocationunits}`
	}

	$panel = $(`<div class="series-panel" id="series-panel_${metadata.resultid}">`)
	$panel.append(`<input id="plot-series-check_${metadata.resultid}"` + 
		`class="plottable-series" type="checkbox" </input>`);
	$panel.append(`<span>` +
		`${metadata.variablecode} ` + 
		`(${metadata.unitsabbreviation}) </br>` +
		`${metadata.samplingfeaturecode} `+
		`(${metadata.sampledmediumcv}`+
		`${zlocation_text}) </br>` +
		`<span class="uuid">UUID: ${metadata.resultuuid}</span>` +
		`</span>`);
	return $panel
}

function getEmptyAxis() {
	for(i=0; i<_axes.length; i++) {
		if (_axes[i] == -999 ) {
			return i;
		};
	}
	//error handling needed - add warning cannot plot empty
	return -1;
}

function unPlotSeries(resultid) {
	for(i=0; i<_axes.length; i++) {
		if (_axes[i] == resultid) {
			removeSeries(i);
			_axes[i] = -999;
		};
	}
}

function plotSeries(response_data) {
	response_json = JSON.parse(response_data);
	resultid = response_json.result_id;
	x = Object.values(response_json.data.valuedatetime)
	y = Object.values(response_json.data.datavalue)
	metadata = _resultMetadata[resultid]
	axis = getEmptyAxis()
	_axes[axis] = resultid;
	addSeries(axis, metadata, x, y);
}

function ajax(request_data, callback_success, callback_fail, url='../../dataloader/ajax/') {
    $.ajax({
        url: url,
        data: {request_data: JSON.stringify(request_data)},
        method: 'POST',
		success: function(response) {
			if (typeof (callback_success) !== 'undefined') {
                callback_success(response);
            }
            else if (typeof (response) !== 'undefined') {
                return response	;
            }
		},
		fail: function(response) {
			if (typeof (callback_fail) !== 'undefined') {
                callback_fail(response);
            }
            else if (typeof (response) !== 'undefined') {
                return response	;
            }
		}
	});
}

function getSamplingFeatureMetadata(sampling_feature_code) {
	request_data = {
		method: 'get_sampling_feature_metadata',
		sampling_feature_code: sampling_feature_code
	}
	ajax(request_data, initAddSeries);
}


function getTimeseriesData(resultid, startdate, enddate) {
	request_data = {
		method: 'get_result_timeseries',
		resultid: resultid,
		startdate: startdate,
		enddate: enddate
	}
	ajax(request_data, plotSeries);
}


