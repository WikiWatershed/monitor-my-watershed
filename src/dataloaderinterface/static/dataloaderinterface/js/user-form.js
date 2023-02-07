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

function setMode(mode) {
            if (mode === "edit") {
                $("[data-profile-mode='view']").toggleClass("hidden", true);
                $("[data-profile-mode='edit']").toggleClass("hidden", false);
                $("#btn-edit-profile").removeClass("fab-trans");
                $("#btn-cancel-profile-edit").addClass("fab-trans");
                $("#btn-update-user").addClass("fab-trans");
            }
            else {
                $("[data-profile-mode='edit']").toggleClass("hidden", true);
                $("[data-profile-mode='view']").toggleClass("hidden", false);
                $("#btn-edit-profile").addClass("fab-trans");
                $("#btn-cancel-profile-edit").removeClass("fab-trans");
                $("#btn-update-user").removeClass("fab-trans");
            }
}

function getFormData(form_id) {
    let $form = (`#${form_id}`)

    let data = {};
    $($form).children().find('.form-field').each( function() {
        let id = $(this).prop('id');
        let parameter_name = id.split('id_',2)[1];
        let value = $(this).val();
        data[parameter_name] = value; 
    });
    return data;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function initializeOrganizationSelect() {
    organizations = await $.ajax({
        url : '/api/organizations/',
        method : 'GET'
    });
    let $organization_select = $('#id_organization_id')
    let org = $organization_select.attr('org');
    $organization_select.empty()
    organizations.forEach(function(organization) {
        $($organization_select).append(
            $('<option>', {
                value : organization.organizationid,
                text : organization.organizationname,
            })
        );
    });
    $organization_select.val(org);
    
    initializeSelect($organization_select);
    $('<option value="new">Add New Organization...</option>').insertBefore($organization_select.children().first());
    $organization_select.on('change', function() {
        if ($(this).val() === 'new') {
            cleanOrganizationForm();
            $('#organization-dialog').modal('toggle');
        }
    });
}

$(document).ready(function() {
    
    $("#btn-edit-profile").on("click", function(){
        initializeOrganizationSelect();
        setMode("edit");
    });

    $("#btn-cancel-profile-edit").on("click", function(){
        setMode("view");
    });

    if ($(".user-registration .alert-error").length > 0) {
        setMode("edit");
    }

    $("#btn-update-user").on("click", function() {
        let formData = getFormData('profile-form');
        $.ajax({
            url : '/update_account/',
            headers: { "X-CSRFToken": getCookie("csrftoken")}, 
            method : 'POST',
            data : formData,
            success : function(response) {
                location.reload();
            },
            error : function(response) {
                alert(response.responseText);
            },


        });
    });
    
    var organizationForm = $('div.organization-fields');


    $('#new-organization-button').on('click', function() {
        clearFieldErrors($('.organization-fields .has-error'));
        var data = $('.organization-fields input, .organization-fields select').toArray().reduce(function(dict, field) {
            dict[field.name] = field.value;
            return dict;
        }, {});

        $.ajax({
            url: '/api/organization/',
            type: 'post',
            data: $.extend({
                csrfmiddlewaretoken: $('form input[name="csrfmiddlewaretoken"]').val()
            }, data)
        }).done(function(data, message, xhr) {
            if (xhr.status === 201) {
                // organization created
                $('#id_organization_id').attr('org',data.organization_id);
                initializeOrganizationSelect();
                $('#organization-dialog').modal('toggle');
            } else if (xhr.status === 206) {
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
        var organizationSelect = $('.user-fields select[name="organization_code"]');
        organizationSelect.val('');
        initializeSelect(organizationSelect);
    });
});
