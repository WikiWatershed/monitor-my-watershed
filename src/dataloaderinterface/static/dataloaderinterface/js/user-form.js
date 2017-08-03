/**
 * Created by Juan on 12/12/2016.
 */


function cleanOrganizationForm() {
    $('.organization-fields input, .organization-fields select').val('');
    initializeSelect($('.organization-fields select'));
}

function generateErrorList(errors) {
    var list = $('<ul class="errorlist"></ul>');
    errors.forEach(function(error) {
        list.append($('<li>' + error + '</li>'));
    });

    return list;
}

$(document).ready(function() {
    var organizationForm = $('.organization-fields');
    var organizationSelect = $('form').find('[name="organization"]');
    initializeSelect(organizationForm.find('[name="organization_type"]'));

    $('<option value="new">Add New Organization</option>').insertAfter(organizationSelect.children().first());
    organizationSelect.on('change', function() {
        if ($(this).val() == 'new') {
            cleanOrganizationForm();
            $('#organization-dialog').modal('toggle');
        }
    });

    $('#new-organization-button').on('click', function() {
        clearFieldErrors($('.organization-fields .has-error'));
        var data = $('.organization-fields input, .organization-fields select').toArray().reduce(function(dict, field) {
            dict[field.name] = field.value;
            return dict;
        }, {});
        
        $.ajax({
            url: $('#new-organization-api').val(),
            type: 'post',
            data: $.extend({
                csrfmiddlewaretoken: $('form input[name="csrfmiddlewaretoken"]').val()
            }, data)
        }).done(function(data, message, xhr) {
            if (xhr.status == 201) {
                // organization created
                var newOption = $('<option value="' + data.organization_id + '">' + data.organization_name + '</option>');
                $('.user-fields select[name="organization"]').append(newOption).val(data.organization_id);
                $('#organization-dialog').modal('toggle');
            } else if (xhr.status == 206) {
                // organization form error
                var form = $('.organization-fields');

                for (var fieldName in data) {
                    if (!data.hasOwnProperty(fieldName)) {
                        continue;
                    }

                    var element = form.find('[name="' + fieldName + '"]');
                    var field = element.parents('.form-field');
                    var errors = generateErrorList(data[fieldName]);
                    field.addClass('has-error');
                    field.append(errors);

                    element.on('change keypress', function(event, isTriggered) {
                        if (isTriggered) {  // http://i.imgur.com/avHnbUZ.gif
                            return;
                        }

                        var fieldElement = $(this).parents('div.form-field');
                        clearFieldErrors(fieldElement);
                    });
                }
            }
        }).fail(function(data) {
            console.log(data);
        });
    });

    $('#organization-modal-close').on('click', function() {
        var organizationSelect = $('.user-fields select[name="organization"]');
        organizationSelect.val('');
        initializeSelect(organizationSelect);
    });
});
