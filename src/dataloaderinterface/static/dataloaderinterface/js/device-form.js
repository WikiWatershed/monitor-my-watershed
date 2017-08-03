// (function() {
//     'use strict';
//
// }());

function updateSitePosition(map, position) {
    map.panTo(position);
    $('input[name="latitude"]').val(Math.round(position.lat() * 100000) / 100000).trigger('keypress');
    $('input[name="longitude"]').val(Math.round(position.lng() * 100000) / 100000).trigger('keypress');
}

function updateSiteElevation(position) {
    var elevator = new google.maps.ElevationService();
     elevator.getElevationForLocations({'locations':[position]}, function(results, status) {
          if (status == google.maps.ElevationStatus.OK && results[0]) {
              $('input[name="elevation_m"]').val(Math.round(results[0].elevation)).trigger('keypress');
          }
     });
}

function initMap() {
    const DEFAULT_ZOOM = 4;
    const DEFAULT_SPECIFIC_ZOOM = 10;
    const DEFAULT_LATITUDE = 37.0902;
    const DEFAULT_LONGITUDE = -95.7129;
    var mapTip = $('<div class="map-info"><span><i class="fa fa-info-circle" aria-hidden="true"></i> Click on the map to update coordinates and elevation data</span></div>');
    var mapPosition = { lat: parseFloat($('input[name="latitude"]').val()), lng: parseFloat($('input[name="longitude"]').val()) };
    var isCompletePosition = mapPosition.lat && mapPosition.lng;
    var mapZoom = parseInt($('input[name="zoom-level"]').val());

    var map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: mapPosition.lat || DEFAULT_LATITUDE, lng: mapPosition.lng || DEFAULT_LONGITUDE },
        zoom: mapZoom || DEFAULT_ZOOM,
        mapTypeId: google.maps.MapTypeId.TERRAIN,
        scrollwheel: false,
        draggableCursor: 'pointer',
        disableDefaultUI: true,
        zoomControl: true,
        zoomControlOptions: {
          position: google.maps.ControlPosition.LEFT_BOTTOM
        },
        scaleControl: true
    });

    var marker = new google.maps.Marker({
        position: (mapPosition.lat && mapPosition.lng)? mapPosition: undefined,
        map: map
    });

    if (navigator.geolocation && !isCompletePosition) {
        navigator.geolocation.getCurrentPosition(function getLocation(locatedPosition) {
            map.setCenter({ lat: locatedPosition.coords.latitude, lng: locatedPosition.coords.longitude });
            map.setZoom(DEFAULT_SPECIFIC_ZOOM);
        }, undefined, { timeout: 5000 });
    }

    map.controls[google.maps.ControlPosition.TOP_CENTER].push(mapTip.get(0));

    map.addListener('click', function(event) {
        marker.setPosition(event.latLng);
        updateSitePosition(map, event.latLng);
        updateSiteElevation(event.latLng);
    });
    
    map.addListener('zoom_changed', function() {
        $('input[name="zoom-level"]').val(map.getZoom());
    });

    $('input[name="latitude"], input[name="longitude"]').on('change', function() {
        var coordinates = {
            lat: parseFloat($('input[name="latitude"]').val()),
            lng: parseFloat($('input[name="longitude"]').val())
        };

        if (!coordinates.lat || !coordinates.lng) {
            return;
        }

        map.panTo(coordinates);
        marker.setPosition(coordinates);
    });
}


function applyInstrumentOutputFilter(equipmentModelSelect) {
    var resultForm = equipmentModelSelect.parents('.result-form');
    var variableSelect = resultForm.find('[name$="variable"]');
    var unitSelect = resultForm.find('[name$="unit"]');

    var outputVariables = equipmentModelSelect
        .find('option[value=' + equipmentModelSelect.val() + ']')
        .data('output-variables');

    filterSelectOptions(variableSelect, Object.keys(outputVariables.variables));
    filterSelectOptions(unitSelect, Object.keys(outputVariables.units));

    variableSelect.data('filters-applied', false);
    unitSelect.data('filters-applied', false);

    if (variableSelect.val()) {
        variableSelect.trigger('change');
    } else if (unitSelect.val()) {
        unitSelect.trigger('change');
    }
}

function bindResultEvents(resultForm) {
    var equipmentModelSelect = resultForm.find('[name$="equipment_model"]');
    var variableSelect = resultForm.find('[name$="variable"]');
    var unitSelect = resultForm.find('[name$="unit"]');

    // equipment model selection
    equipmentModelSelect.on('change', function() {
        var resultForm = $(this).parents('.result-form');

        // clear filter if no model was selected.
        var modelId = $(this).val();
        if (!modelId) {
            clearSelectFilter(resultForm.find('[name$="variable"]').add(resultForm.find('[name$="unit"]')));
            return;
        }

        var selectedOption = equipmentModelSelect.find('option[value=' + modelId + ']');
        // just apply filter if there's a cached map of output variables.
        if (selectedOption.data('output-variables')) {
            applyInstrumentOutputFilter(equipmentModelSelect);
            return;
        }

        // request output variables
        requestFilteredOptions(
            $('#model-variables-api').val(),
            { equipment_model_id: modelId, csrfmiddlewaretoken: $('form').find('[name="csrfmiddlewaretoken"]').val() },
            function(data) {
                var variablesMap = data.reduce(function(map, outputVariable) {
                    var units = map[outputVariable.variable] || [];
                    units.push(outputVariable.instrument_raw_output_unit.toString());
                    map[outputVariable.variable] = units;
                    return map;
                }, {});

                var unitsMap = data.reduce(function(map, outputUnit) {
                    var variables = map[outputUnit.instrument_raw_output_unit] || [];
                    variables.push(outputUnit.variable.toString());
                    map[outputUnit.instrument_raw_output_unit] = variables;
                    return map;
                }, {});

                selectedOption.data('output-variables', { variables: variablesMap, units: unitsMap });
                applyInstrumentOutputFilter(equipmentModelSelect);
            }
        );
    });
    equipmentModelSelect.trigger('change', [true]);


    variableSelect.on('change', function() {
        var resultForm = $(this).parents('.result-form');
        var modelId = equipmentModelSelect.val();
        var variableId = $(this).val();

        if ($(this).data('filters-applied') || !modelId) {
            return;
        }

        if (!variableId) {
            resultForm.find('[name$="equipment_model"]').trigger('change', [true]);
            return;
        }

        var outputVariableData = equipmentModelSelect.find('option[value=' + modelId + ']').data('output-variables');
        unitSelect.data('filters-applied', true);

        filterSelectOptions(unitSelect, outputVariableData.variables[variableId]);
    });
    variableSelect.trigger('change', [true]);


    unitSelect.on('change', function() {
        var resultForm = $(this).parents('.result-form');
        var modelId = equipmentModelSelect.val();
        var unitId = $(this).val();

        if ($(this).data('filters-applied') || !modelId) {
            return;
        }

        if (!unitId) {
            resultForm.find('[name$="equipment_model"]').trigger('change', [true]);
            return;
        }

        var outputVariableData = equipmentModelSelect.find('option[value=' + modelId + ']').data('output-variables');
        variableSelect.data('filters-applied', true);

        filterSelectOptions(variableSelect, outputVariableData.units[unitId]);
    });
    unitSelect.trigger('change', [true]);
}

function initializeResultsForm() {
    var form = $('div#result-dialog .result-form');
    bindResultEvents(form);
    selectSoloOptions(form.find('select'));
    initializeSelect(form.find('select.form-control'));
    
    $('div#result-dialog').on('show.bs.modal', function(event) {
        if (event.relatedTarget && event.relatedTarget.id === 'new-result-button') {
            $(this).find('#add-sensor-button').show();
            $(this).find('#edit-sensor-button').hide();
            var fields = form.find('select');
            var fieldsParents = fields.parents('div.form-field');
            clearSelectFilter(fields);
            fields.val('');

            if (fieldsParents.hasClass('has-error')) {
                fieldsParents.find('.errorlist').remove();
                fieldsParents.removeClass('has-error');
            }
        } else {
            $(this).find('#add-sensor-button').hide();
            $(this).find('#edit-sensor-button').show();
        }
    });

    $('div#result-dialog button#add-sensor-button').on('click', function() {
        validateResultForm().done(function(data, message, xhr) {
            if (xhr.status == 200) {
                // valid
                var rows = $('div#formset tr.result-form');
                var highestIndex = rows.toArray().reduce(function(value, current, index, list) {
                    var currentValue = parseInt(current.dataset.result.replace('form-', ''));
                    return Math.max(value, currentValue);
                }, -1);
                var newIndex = highestIndex + 1;
                $('input[name="form-TOTAL_FORMS"]').val(rows.length + 1);
        
                var newRow = $($('#sensor-row').html().replace(new RegExp('__prefix__', 'g'), newIndex));
                updateRowData(newRow);
                bindResultEditEvent(newRow);
                bindResultDeleteEvent(newRow);
        
                $('div.results-table table').append(newRow);
                $('#result-dialog').modal('toggle');
                
            } else if (xhr.status == 206) {
                // not valid
                var form = $('div#result-dialog div.result-form');
                for (var fieldName in data) {
                    var element = form.find('[name*="' + fieldName + '"]');
                    var field = element.parents('.form-field');
                    field.addClass('has-error');

                    form.find('div.form-field.has-error .form-control').on('change keypress', function(event, isTriggered) {
                        if (isTriggered) {  // http://i.imgur.com/avHnbUZ.gif
                            return;
                        }

                        var fieldElement = $(this).parents('div.form-field');
                        if (fieldElement.hasClass('has-error')) {
                            fieldElement.find('.errorlist').remove();
                            fieldElement.removeClass('has-error');
                        }
                    });
                }
            }
        });
    });

    $('div#result-dialog button#edit-sensor-button').on('click', function() {
        var dialog = $('#result-dialog');
        var row = dialog.data('row');
        updateRowData(row);
        dialog.modal('toggle');
    });
}

function validateResultForm() {
    var prefixText = '-__prefix__-';
    var data = $('#result-dialog div.result-form input, #result-dialog div.result-form select').toArray().reduce(function(dict, field) {
        var fieldName = field.name.substring(field.name.indexOf(prefixText) + prefixText.length, field.name.length);
        dict[fieldName] = field.value;
        return dict;
    }, {});
    
    return $.ajax({
        url: $('#result-validation-api').val(),
        type: 'post',
        data: $.extend({ csrfmiddlewaretoken: $('form input[name="csrfmiddlewaretoken"]').val() }, data)
    });
}

function fillFormData(row) {
    row.find('td[data-field]').each(function(index, column) {
        var fieldName = $(column).data('field');
        var selectedValue = $(column).find('input').val();
        var formSelect = $('div#result-dialog div.result-form .form-control[name*="' + fieldName + '"]');
        formSelect.val(selectedValue);
        formSelect.trigger('change');
    });
    $('#result-dialog').data('row', row);
}

function updateRowData(row) {
    var prefixText = '-__prefix__-';
    var fields = $('div#result-dialog div.result-form .form-control');
    for (var index = 0; index < fields.length; index++) {
        var field = fields.get(index);
        var selectedOption = $(field).find('option:selected');
        var fieldName = field.name.substring(field.name.indexOf(prefixText) + prefixText.length, field.name.length);
        var dataColumn = row.find('td[data-field="' + fieldName + '"]');
        dataColumn.find('.field-text').text(selectedOption.text());
        dataColumn.find('.field-value').val(selectedOption.val());
    }
}

function bindResultEditEvent(row) {
    row.find('td[data-behaviour="edit"] button').on('click', function(event) {
        fillFormData($(this).parents('tr'));
        $('#result-dialog').modal('toggle');
    });
}

function bindResultDeleteEvent(row) {
    row.find('td[data-behaviour="delete"] button').on('click', function(event) {
        var sensor = $(this).parents('tr');
        $('#confirm-delete').data('to-delete', sensor).modal('toggle');
    });
}

function initializeResultsTable() {
    var rows = $('div.results-table tbody tr');
    bindResultEditEvent(rows);
    bindResultDeleteEvent(rows);
}

$(document).ready(function() {
    $('nav .menu-register-site').addClass('active');

    initializeResultsForm();
    initializeResultsTable();

    $('#btn-confirm-delete').on('click', function(event) {
        var dialog = $('#confirm-delete');
        // var totalForms = $('input[name="form-TOTAL_FORMS"]');
        // totalForms.val(totalForms.val() - 1);

        dialog.data('to-delete').addClass('deleted-row').find('input[name*="DELETE"]').prop('checked', true);
        dialog.modal('toggle');
    });
});
