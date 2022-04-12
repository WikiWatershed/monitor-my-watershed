var _resultMetadata = {};
var _resultsTimeSeries = {};

var min_date;
var max_date;

var _init = true;

$(function () {
	initChart('cht_ts');
	//default to last year for xaxis
	max_date = new Date(Date.now());
	min_date = new Date(Date.now());
	min_date.setFullYear(min_date.getFullYear() - 1);
	updatePlotDateRange(min_date, max_date);

	if (_samplingfeaturecode !== undefined) {
		getSamplingFeatureMetadata(_samplingfeaturecode);
	}

	ajax({method:'get_sampling_features'}, populateSamplingFeatureSelect);

	$(document).on('click', '.plottable-series', function() {
		let resultid = $(this).attr('id').split("_")[1];
		let checked = $(this).prop('checked');
		changeTimeSeries(resultid, checked);
	});

	$('#load-site').on('click', function() {
		let samplingfeaturecode = $('#site-select').find(':selected').prop('id');
		getSamplingFeatureMetadata(samplingfeaturecode);
	});

	$('#btnSetPlotOptions').on('click', function() {
		let min = $('#dpd1').val();
		min_date = null;
		if (min !== '') {min_date = new Date(min);}
		let max = $('#dpd2').val();
		max_date = null;
		if (max !== '') {max_date = new Date(max);}
		updatePlotDateRange(min_date, max_date);
	});

	$('#btnLastYear').on('click', function() {
		max_date = new Date(Date.now());
		min_date = new Date(Date.now());
		min_date.setFullYear(min_date.getFullYear() - 1);
		updatePlotDateRange(min_date, max_date);
	});

	$('#btnLastMonth').on('click', function() {
		max_date = new Date(Date.now());
		min_date = new Date(Date.now());
		min_date.setMonth(min_date.getMonth() - 1);
		updatePlotDateRange(min_date, max_date);
	})

	$('#btnAll').on('click', function() {
		min_date = null;
		max_date = null;
		updatePlotDateRange(min_date, max_date);
	});

	$('#sites-filter').on('change', function() {
		let filter_text = $('#sites-filter').val().toLowerCase();
		$('#site-select option').each(function(index, element) {
			if (element.innerText.toLowerCase().includes(filter_text)) {
				$(element).show();
			}
			else {
				$(element).hide();
			}
		});
	});

	$('#series-filter').on('change', function() {
		let filter_text = $('#sites-filter').val().toLowerCase();
		let $series = $('#plottableSeries')
		$series.find('.series-panel').each(function(index, element) {
			if (element.innerText.toLowerCase().includes(filter_text)) {
				$(element).show();
			}
			else {
				$(element).hide();
			}
		});
	});

	$('.message-box>input').on('click', function(){
		$('.message-box').hide();
	});

});

function displayMessage(title, msg) {
	$('.message-box #title').text(title);
	$('.message-box #msg').text(msg);
	$('.message-box').show();
}

function dateToString(date) {
	if (date !== null && date !== undefined) {
		let year = date.getUTCFullYear();
		let month = ("0" + (date.getUTCMonth() + 1)).slice(-2);
		let day = ("0" + date.getUTCDate()).slice(-2);
		return `${year}-${month}-${day}`;
	}	
	return '';
}

function updatePlotDateRange(min, max) {
	$('#dpd1').val('');
	$('#dpd2').val('');
	if (min != null) {
		$('#dpd1').val(dateToString(min));
		min = min.getTime();
	}
	if (max != null) {
		$('#dpd2').val(dateToString(max));
		max = max.getTime() + 86399; //select end of day as end point
	}	
	_chart.xAxis[0].update({'min':min, 'max':max}); 
	_chart.xAxis[0].setExtremes();
}

async function changeTimeSeries(result_id, checked) {
	let $plotted = $('#plottedSeries');
	let $notplotted = $('#plottableSeries');
	let $panel = $(`#series-panel_${result_id}`)
	let $input = $panel.find('input')
	if ($plotted.children().length == 6 && checked) {
		$($input).prop("checked",false);
		displayMessage("Warning: Too Many Time Series Selected", 
			"A maximum of six(6) time series can be plotted at a single time. Please " +
			"remove a plot series by unchecking it prior to plotting any additional " +
			"time series."
		);
		return;
	}

	$input.prop('disabled', true);
	if (checked) {
		$panel.remove();
		$plotted.append($panel);
		if (result_id in _resultsTimeSeries) {
			plotSeries(_resultsTimeSeries[result_id], result_id)
			$input.prop('disabled', false);
		}
		else {
			$input.prop('disabled', false);
			let timeseries = await TimeSeries.build(result_id, min_date, max_date);
			_resultsTimeSeries[result_id] = timeseries;	
		} 
	}
	if (!checked) { 
		unPlotSeries(result_id);
		$panel.remove();
		$notplotted.append($panel);
		$input.prop('disabled', false);
	}
}

function initAddSeries(response) {
	let response_obj = JSON.parse(response);
	for (let [index, metadata] of Object.entries(response_obj)) {
		_resultMetadata[metadata.resultid] = metadata
	}	
	populateSeriesBlock();
	if (_init) {
		_init = false;
		if (_result_id !== undefined && _result_id !== '') {
			changeTimeSeries(_result_id, true);
			$(`#plot-series-check_${_result_id}`).prop('checked', true);
		}
	}
}

function populateSeriesBlock(){
	let $block = $('#plottableSeries')
	$block.empty();
	for (let [key, metadata] of Object.entries(_resultMetadata)) {
		let $panel = makeSeriesPanel(metadata);
		$block.append($panel);
	}	
}

function makeSeriesPanel(metadata) {
	let zlocation_text = ''
	if (metadata.zlocation !== undefined && metadata.zlocation !== null) {
		zlocation_text = `: ${metadata.zlocation} ${metadata.zlocationunits}`
	}

	let $panel = $(`<div class="series-panel" id="series-panel_${metadata.resultid}">`)
	$panel.append(`<input id="plot-series-check_${metadata.resultid}"` + 
		`class="plottable-series" type="checkbox" </input>`);
	$panel.append(`<span>` +
		`${metadata.samplingfeaturecode} `+
		`(${metadata.sampledmediumcv}`+
		`${zlocation_text}) </br>` +
		`${metadata.variablecode} ` + 
		`(${metadata.unitsabbreviation}) </br>` +
		`<span class="uuid">UUID: ${metadata.resultuuid}</span>` +
		`</span>`);
	return $panel
}

function getEmptyAxis() {
	for(let i=0; i<_axes.length; i++) {
		if (_axes[i] == -999 ) {
			return i;
		};
	}
	return -1;
}

function unPlotSeries(resultid) {
	for(let i=0; i<_axes.length; i++) {
		if (_axes[i] == resultid) {
			removeSeries(_chart, i);
			_axes[i] = -999;
		};
	}
}

function getTimeseriesDataCallback(response_data, request_data) {
	let response_json = JSON.parse(response_data);
	let resultid = request_data.resultid;	
	_resultsTimeSeries[resultid] = {
		'x':Object.values(response_json.valuedatetime), 
		'y':Object.values(response_json.datavalue)
	};
	plotSeries(_resultsTimeSeries[resultid],resultid);
}

function plotSeries(timeseriesData, resultid) {
	let x = timeseriesData['x'];
	let y = timeseriesData['y'];
	let metadata = _resultMetadata[resultid]
	let axis = getEmptyAxis()
	if (axis >= 0) {
		_axes[axis] = resultid;

		let zlocation_text = ''
		if (metadata.zlocation !== undefined && metadata.zlocation !== null) {
			zlocation_text = `: ${metadata.zlocation} ${metadata.zlocationunits}`
		}

		let axis_title =  `[${metadata.samplingfeaturecode} ${metadata.sampledmediumcv} ${zlocation_text}] ` +
			`${metadata.variablecode} (${metadata.unitsabbreviation})`;
		
		addSeries(_chart, axis, axis_title, axis_title, x, y);
	}
}

function ajax(request_data, callback_success, callback_fail, url='/dataloader/ajax/') {
    $.ajax({
        url: url,
        data: {request_data: JSON.stringify(request_data)},
        method: 'POST',
		success: function(response) {
			if (typeof (callback_success) !== 'undefined') {
                callback_success(response, request_data);
            }
            else if (typeof (response) !== 'undefined') {
                return response	;
            }
		},
		fail: function(response) {
			if (typeof (callback_fail) !== 'undefined') {
                callback_fail(response, request_data);
            }
            else if (typeof (response) !== 'undefined') {
                return response	;
            }
		}
	});
}

function getSamplingFeatureMetadata(sampling_feature_code) {
	let request_data = {
		method: 'get_sampling_feature_metadata',
		sampling_feature_code: sampling_feature_code
	}
	ajax(request_data, initAddSeries);
}

function getTimeseriesData(resultid, startdate, enddate) {
	let request_data = {
		method: 'get_result_timeseries',
		resultid: resultid,
		startdate: startdate,
		enddate: enddate
	}
	ajax(request_data, getTimeseriesDataCallback);
}

function populateSamplingFeatureSelect(response) {
	let $select = $('#site-select');
	$select.empty();

	let data = JSON.parse(response);
	
	for (let [index, samplingFeature] of Object.entries(data)) {
		var selected = ''
		if (samplingFeature.samplingfeaturecode == _samplingfeaturecode) {
			selected = 'selected'
		}
		let option = `<option id="${samplingFeature.samplingfeaturecode}" ` +
			`${selected} >` + 
			`(${samplingFeature.samplingfeaturecode}) ` +
			`${samplingFeature.samplingfeaturename}</option>`;
		$select.append(option);
	}	
}
