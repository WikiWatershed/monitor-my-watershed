var _resultMetadata = {};
var _resultsTimeSeries = {};

var minDate;
var maxDate;

var _init = true;

$(function () {
	initChart('cht_ts');
	//default to last year for xaxis
	maxDate = new Date(Date.now());
	minDate = new Date(Date.now());
	minDate.setFullYear(minDate.getFullYear() - 1);
	updatePlotDateRange(minDate, maxDate);

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
		minDate = null;
		if (min !== '') {minDate = new Date(min);}
		let max = $('#dpd2').val();
		maxDate = null;
		if (max !== '') {maxDate = new Date(max);}
		updatePlotDateRange(minDate, maxDate);
	});

	$('#btnLastYear').on('click', function() {
		maxDate = new Date(Date.now());
		minDate = new Date(Date.now());
		minDate.setFullYear(minDate.getFullYear() - 1);
		updatePlotDateRange(minDate, maxDate);
	});

	$('#btnLastMonth').on('click', function() {
		maxDate = new Date(Date.now());
		minDate = new Date(Date.now());
		minDate.setMonth(minDate.getMonth() - 1);
		updatePlotDateRange(minDate, maxDate);
	})

	$('#btnAll').on('click', function() {
		minDate = null;
		maxDate = null;
		updatePlotDateRange(minDate, maxDate);
	});

	$('#sites-filter').on('change', function() {
		let filterText = $('#sites-filter').val().toLowerCase();
		$('#site-select option').each(function(index, element) {
			if (element.innerText.toLowerCase().includes(filterText)) {
				$(element).show();
			}
			else {
				$(element).hide();
			}
		});
	});

	$('#series-filter').on('change', function() {
		let filterText = $('#sites-filter').val().toLowerCase();
		let $series = $('#plottableSeries')
		$series.find('.series-panel').each(function(index, element) {
			if (element.innerText.toLowerCase().includes(filterText)) {
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
	getAdditionalPlotData(new Date(min));
	_chart.xAxis[0].update({'min':min, 'max':max}); 
	_chart.xAxis[0].setExtremes();
}

function getAdditionalPlotData(startDate) {
	for(let i=0; i<_axes.length; i++) {
		let resultId = _axes[i]
		if (resultId == -999) {continue;}
		let timeseries = _resultsTimeSeries[resultId];
		loadDataAndUpdateSeries(i, startDate, timeseries)
	}
}

async function loadDataAndUpdateSeries(index, startDate, timeseries) {
	await timeseries.loadData(startDate);
	updateSeries(_chart, index, timeseries.dates, timeseries.values);
}

async function changeTimeSeries(resultId, checked) {
	let $plotted = $('#plottedSeries');
	let $notplotted = $('#plottableSeries');
	let $panel = $(`#series-panel_${resultId}`)
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
		if (resultId in _resultsTimeSeries) {
			let timeseries = _resultsTimeSeries[resultId];
			timeseries.loadData(minDate)
			plotSeries(timeseries.resultId, timeseries.axisLabel(), timeseries.dates, timeseries.values)
			$input.prop('disabled', false);
		}
		else {
			let metadata = _resultMetadata[resultId]
			let timeseries = await TimeSeries.build(resultId, minDate, maxDate, metadata);
			_resultsTimeSeries[resultId] = timeseries;	
			plotSeries(timeseries.resultId, timeseries.axisLabel(), timeseries.dates, timeseries.values)
			$input.prop('disabled', false);
		} 
	}
	if (!checked) { 
		unPlotSeries(resultId);
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

function plotSeries(resultId, axisTitle, x, y) {
	let axis = getEmptyAxis()
	if (axis >= 0) {
		_axes[axis] = resultId;
		addSeries(_chart, axis, axisTitle, x, y);
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
