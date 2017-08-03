/**
 * Created by Juan on 11/28/2016.
 */

function initializeSelect(select) {
    setTimeout(function () {
        select.each(function(index, selectElement) {
            $(selectElement).select2({
                theme: "bootstrap",
                containerCssClass : "input-sm",
                dropdownAutoWidth: true,
                width: 'auto',
                allowClear: true,
                placeholder: $(selectElement).attr('placeholder')
            });
        });
    });
}

function selectSoloOptions(select) {
    select.each(function() {
        var selectElement = $(this);
        var options = selectElement.children('[value!=""]:not([disabled])');
        if (options.length === 1) {
            selectElement.val(options.get(0).value);
            selectElement.trigger('change')
        }
    });
}

function requestFilteredOptions(serviceUrl, requestOptions, callback) {
    $.ajax({ url: serviceUrl, data: requestOptions })
        .done(callback)
        .fail(function(xhr, error) {
            console.log(error);
        })
        .always(function(response, status, xhr) {
            console.log(status + ": " + xhr.responseText);
        });
}

function filterSelectOptions(select, values) {
    select.children('option').each(function(index, element) {
        if (values.indexOf(element.value) === -1 && element.value !== '') {
            $(element).attr('disabled', 'disabled');
        } else {
            $(element).removeAttr('disabled');
        }
    });

    if (values.indexOf(select.val()) === -1) {
        select.val('');
    }

    selectSoloOptions(select);
    initializeSelect(select);
}


function clearSelectFilter(select) {
    select.children('option').removeAttr('disabled');
    initializeSelect(select);
}

function clearFieldErrors(field) {
    if (field.hasClass('has-error')) {
        field.find('.errorlist').remove();
        field.removeClass('has-error');
    }
}

$(document).ready(function() {
    var form = $('form');
    selectSoloOptions(form.find('select'));
    initializeSelect(form.find('select.form-control'));
    
    $('div.form-field.has-error .form-control').on('change keypress', function(event, isTriggered) {
        if (isTriggered) {  // http://i.imgur.com/avHnbUZ.gif
            return;
        }

        var fieldElement = $(this).parents('div.form-field');
        clearFieldErrors(fieldElement);
    });

    $(document).on("keypress", ":input:not(textarea):not([type=submit])", function(event) {
        if (event.keyCode == 13) {
            event.preventDefault();
        }
    });
});
