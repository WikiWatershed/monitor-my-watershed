/**
 * Created by Mauriel on 6/5/2018.
 */

output_variables = {};

filter_structure = {
    'sensor_manufacturer': {sub_filters: ['sensor_model']},
    'sensor_model': {sub_filters: ['variable', 'sensor_manufacturer']},
    'variable': {sub_filters: ['unit', 'sampled_medium', 'sensor_model']},
    'unit': {sub_filters: ['variable']},
    'sampled_medium': {sub_filters: ['variable']}
};

function defaultSensorsMessage() {
    $("tr.no-sensors-row").toggleClass("hidden", !!$("tr.result-form:not(.deleted-row)").length);
}

function updateRowData(row) {
    var fields = $('div#result-dialog div.result-form input, div#result-dialog div.result-form select');

    for (var index = 0; index < fields.length; index++) {
        var field = $(fields.get(index));
        var fieldName = field.attr('name');
        var value = field.val();
        row.data(fieldName, value);

        if (field.hasClass('form-control')) {
            var selectedOption = field.find('option:selected');
            var dataColumn = row.find('td[data-field="' + fieldName + '"]');
            dataColumn.find('.field-text').text(selectedOption.text());
        }
    }
}

function clear_filters() {
    var form = $('div#result-dialog .result-form');
    for (var filter_name in filter_structure) {
        if (!filter_structure.hasOwnProperty(filter_name)) {
            continue;
        }

        var select = form.find('select[name$="' + filter_name + '"]');
        var filter = filter_structure[filter_name];

        if (filter.filtered_set) {
            filter.filtered_set.length = 0;
        }
        filter.filtered_by = undefined;

        select.val('');
        select.trigger('change');
    }
}

function apply_filter(filter_name, values, parent_filter_name) {
    var filter = filter_structure[filter_name];
    var parent_filter = filter_structure[parent_filter_name];
    var has_selected_values = !(values.length === 1 && values[0] === '');
    var filtered_set = parent_filter && parent_filter.filtered_set || output_variables;

    if (has_selected_values) {
        filtered_set = filtered_set.filter(function(output) {
            if (!output.hasOwnProperty(filter_name)) {
                return false;
            }
            return values.indexOf(output[filter_name] && output[filter_name].toString()) >= 0;
        });
    }

    var is_initial_set = output_variables.every(function(item){return filtered_set.indexOf(item) >= 0;});
    filter.filtered_by = (is_initial_set)? undefined: parent_filter_name;
    filter.filtered_set = filtered_set;

    for (var index = 0; index < filter.sub_filters.length; index++) {
        var sub_filter_name = filter.sub_filters[index];

        if (sub_filter_name === parent_filter_name) {
            continue;
        }

        var sub_filter_values = filter.filtered_set.reduce(function(filter_values, output) {
            var value = output[sub_filter_name] && output[sub_filter_name].toString();
            if (filter_values.indexOf(value) < 0) {
                filter_values.push(value);
            }
            return filter_values;
        }, []);

        updateFilterUI(sub_filter_name, sub_filter_values);
        apply_filter(sub_filter_name, sub_filter_values, filter_name);
    }
}

function updateFilterUI(sub_filter, sub_filter_values) {
    var select = $('div#result-dialog .result-form select[name$="' + sub_filter + '"]');
    filterSelectOptions(select, sub_filter_values);
}

function bindResultEvents(form) {
    var filters = Object.keys(filter_structure);
    var output_variable_select = $('div#result-dialog .result-form input[name$="output_variable"]');

    $.ajax({
        url: $('#output-variables-api').val(),
        data: {csrfmiddlewaretoken: $('div.result-form').find('[name="csrfmiddlewaretoken"]').val()}
    }).fail(function (xhr, error) {
        console.log(error);
    }).done(function (data) {
        output_variables = data;
    }).always(function (response, status, xhr) {
        // console.log(status + ": " + xhr.responseText);
    });

    for (var index = 0; index < filters.length; index++) {
        var filter = filter_structure[filters[index]];
        var select = form.find('[name$="' + filters[index] + '"]');

        (function(i, filter, select) {
            select.on('change', function(event, automatic_trigger) {
                if (automatic_trigger) {
                    return;
                }

                output_variable_select.val('');
                apply_filter(filters[i], [$(this).val()], filter.filtered_by);

                if (filter.filtered_set.length === 1) {
                    output_variable_select.val(filter.filtered_set[0].pk);
                }
            });
        })(index, filter, select);
    }
}

function initializeResultsForm() {
    var form = $('div#result-dialog .result-form');
    bindResultEvents(form);
    selectSoloOptions(form.find('select'));
    initializeSelect(form.find('select.form-control'));

    $('div#result-dialog').on('show.bs.modal', function(event) {
        var dialog = $(this);
        var fieldsParents = form.find('select').parents('div.form-field');

        if (fieldsParents.hasClass('has-error')) {
            fieldsParents.find('.errorlist').remove();
            fieldsParents.removeClass('has-error');
        }

        if (event.relatedTarget && event.relatedTarget.id === 'new-result-button') {
            clear_filters();
            form.find('input[name="id"]').val('');
            form.find('input[name="output_variable"]').val('');
            form.find('input[name="height"]').val('');
            form.find('textarea[name="sensor_notes"]').val('');

            dialog.find('.mdl-dialog__title').text("Add New Sensor");
            dialog.find('#add-sensor-button').show();
            dialog.find('#edit-sensor-button').hide();
            $('#result-dialog-uuid').parent().hide();
        } else {
            var row = dialog.data('row');
            dialog.find('.mdl-dialog__title').text("Update Sensor");
            dialog.find('#add-sensor-button').hide();
            dialog.find('#edit-sensor-button').show();
            $('#result-dialog-uuid').text(row['result_uuid']).parent().show();
        }
    });

    $('div#result-dialog button#add-sensor-button').on('click', function() {
        var new_sensor_api = $('#sensor-registration-api').val();
        $("#add-sensor-button").prop("disabled", true).text("ADDING NEW SENSOR...");

        make_sensor_api_request(new_sensor_api).done(function(data, message, xhr) {
            var form = $('div#result-dialog div.result-form');
            var message = "";
            if (xhr.status === 201) {
                // valid
                var newRow = $($('#sensor-row').html());
                form.find('[name="id"]').val(data['id']);
                form.find('[name="result_id"]').val(data['result_id']);
                form.find('[name="result_uuid"]').val(data['result_uuid']);

                updateRowData(newRow);
                $('div.results-table table').append(newRow);
                message = "The new sensor has been added!";
                defaultSensorsMessage();
                $('#result-dialog').modal('hide');
            }
            else if (xhr.status === 206) {
                // not valid
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

                message = "Failed to add sensor.";
            }

            $("#add-sensor-button").prop("disabled", false).text("ADD NEW SENSOR");
            snackbarMsg(message);
        });
    });

    $('div#result-dialog button#edit-sensor-button').on('click', function () {
        var edit_sensor_api = $('#sensor-edit-api').val();
        $("#edit-sensor-button").prop("disabled", true).text("UPDATING SENSOR...");

        make_sensor_api_request(edit_sensor_api).done(function(data, message, xhr) {
            var form = $('div#result-dialog div.result-form');
            var message = "";
            if (xhr.status === 202) {
                // valid
                var row = $('div#result-dialog').data('row');
                form.find('[name="id"]').val(data['id']);
                form.find('[name="result_id"]').val(data['result_id']);
                form.find('[name="result_uuid"]').val(data['result_uuid']);
                updateRowData(row);
                defaultSensorsMessage();
                $('#result-dialog').modal('hide');
                message = "Sensor updated successfully!"
            }
            else if (xhr.status === 206) {
                // not valid
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
                message = "Failed to update sensor."
            }

            $("#edit-sensor-button").prop("disabled", false).text("UPDATE SENSOR");
            snackbarMsg(message);
        });
    });

    // notifyInputStatus();
}

function make_sensor_api_request(api_url) {
    var output_data = $('#result-dialog div.result-form input, #result-dialog div.result-form select, #result-dialog div.result-form textarea').toArray().reduce(function(dict, field) {
        dict[field.name] = field.value;
        return dict;
    }, {});

    return $.ajax({
        url: api_url,
        type: 'post',
        data: $.extend({ csrfmiddlewaretoken: $('div.result-form input[name="csrfmiddlewaretoken"]').val() }, output_data)
    });
}

function fillFormData(row) {
    var rowData = row.data();
    var form = $('div#result-dialog div.result-form');

    for (var field_name in filter_structure) {
        if (!filter_structure.hasOwnProperty(field_name)) {
            continue;
        }

        var formSelect = form.find('.form-control[name="' + field_name + '"]');
        formSelect.val(rowData[field_name]);
        formSelect.trigger('change');
    }

    form.find('input[name="id"]').val(rowData['id']);
    form.find('input[name="output_variable"]').val(rowData['output_variable']);
    form.find('input[name="result_id"]').val(rowData['result_id']);
    form.find('input[name="result_uuid"]').val(rowData['result_uuid']);
    form.find('input[name="height"]').val(rowData['height']);
    form.find('textarea[name="sensor_notes"]').val(rowData['sensor_notes']);

    $('#result-dialog').data('row', row);
}

$('#sensors-table').on('click', 'td[data-behaviour="edit"] button', function () {
    var rowElement = $(this).parents('tr');
    var result_uuid = rowElement.data('result_uuid');

    clear_filters();
    fillFormData(rowElement);

    $('#result-dialog-uuid').text(result_uuid).parent().show();
    $('#result-dialog').modal('show');
});

$('#sensors-table').on('click', 'td[data-behaviour="delete"] button', function () {
    var sensor = $(this).parents('tr');
    $('#confirm-delete').data('to-delete', sensor).modal('show');
});

$(document).ready(function () {
    initializeResultsForm();

    $('#btn-confirm-delete').on('click', function () {
        var dialog = $('#confirm-delete');
        var row = dialog.data('to-delete');
        $("#btn-confirm-delete").prop("disabled", true).text("DELETING...");

        $.ajax({
            url: $('#sensor-delete-api').val(),
            type: 'post',
            data: {
                csrfmiddlewaretoken: $('div.result-form input[name="csrfmiddlewaretoken"]').val(),
                id: row.data('id')
            }
        }).done(function (data, message, xhr) {
            if (xhr.status === 202) {
                // Valid
                row.remove();
                snackbarMsg('Sensor has been deleted!');

            } else if (xhr.status === 206) {
                // Invalid
                snackbarMsg('Sensor could not be deleted!');
            }
        }).fail(function (xhr, error) {
            console.log(error);
        }).always(function (response, status, xhr) {
            $("#btn-confirm-delete").prop("disabled", false).text("DELETE");
            defaultSensorsMessage();
            dialog.modal('hide');
        });
    });

    defaultSensorsMessage();

    $("#id_data_file").change(function() {
        $(".selected-file > span").text(this.files[0].name);
        $(".selected-file").show();
        $("#file-preview-default").hide();
        $("#btn-upload-file").prop("disabled", false);
    });

    $("#btn-upload-file").click(function () {
        var form = $("#form-file-upload"),
            formData = new FormData(),
            formParams = form.serializeArray();

        var file = $("#id_data_file")[0].files[0];
        formData.append("data_file", file);

        $.each(formParams, function (i, val) {
            formData.append(val.name, val.value);
        });

        var url = form.attr("action");

        // Change text to Uploading...
        var uploadFileButton = $("#btn-upload-file");

        uploadFileButton.prop("disabled", true);
        uploadFileButton.find("span").text("Uploading...");

        $.ajax({
            url: url,
            type: "POST",
            data: formData,
            async: true,
            cache: false,
            contentType: false,
            processData: false
        }).done(function (response) {
            console.log(response);
        }).fail(function (error) {
            console.log(error);
        }).always(function () {
            // Restore state
            uploadFileButton.prop("disabled", false);
            uploadFileButton.find("span").text("Upload");
        });
    });
});