/**
* settings-form-dialog.js
* This script performs setup for the hydroshare settings modal.
*/

var siteCode = $('#site-code').val().trim();

function initializeHydroShareSettingsDialog() {
    const hydroshareSettingsForm = $('#hydroshare-settings-form')[0];
    document.body.appendChild(hydroshareSettingsForm);
    const dialog = $('dialog#hydroshare-settings-dialog')[0];
    const showDialogButton = $('#show-hydroshare-settings-dialog')[0];
    const scheduledCB = $('input#id_schedule_type_0')[0];
    const manualCB = $('input#id_schedule_type_1')[0];
    const updateFreqSelect = $('select#id_update_freq')[0];

    if (!showDialogButton) {
        // If showDialogButton is undefined, return immediately and do not register dialog.
        // This most likely happens when the hydroshare resource was not found because
        // the user deleted the resource in hydroshare.org.
        return;
    }

    if (!dialog.showModal) {
        dialogPolyfill.registerDialog(dialog);
    }

    showDialogButton.addEventListener('click', () => {
        dialog.showModal();
        $('label[for="id_pause_sharing"]').removeClass('is-focused');
        toggleUpdateFreqSelect(!!$(manualCB).attr('checked'))
    });

    dialog.querySelector('.close').addEventListener('click', () => {
        dialog.close();
    });

    hydroshareSettingsForm.addEventListener('submit', (e) => {
         e.preventDefault();
         submitForm();
    });

    $(manualCB).change(toggleUpdateFreqSelect);
    $(scheduledCB).change(toggleUpdateFreqSelect);

    /**
     * toggleUpdateFreqSelect
     * @description: Shows the "update frequency" select element when the selected update type is "scheduled".
     * Otherwise hides the "update frequency" select element when the selected upate type is "manual".
     */
    function toggleUpdateFreqSelect(e) {
        const hide = typeof e === 'boolean' ? e : e.target.value.toLowerCase() == 'manual';
        $(updateFreqSelect).attr('hidden', hide);
    }

    function submitForm() {
        let dialogButtons = $(hydroshareSettingsForm).find('.mdl-dialog__actions').find('button');
        $(dialogButtons).removeClass();
        $(dialogButtons).addClass('mdl-button mdl-button--raised');
        $(dialogButtons).prop('disabled', true);

        let submitButton = $(hydroshareSettingsForm).find('button[type=submit]')[0];

        let method = submitButton.id === 'create-resource' ? 'create' : 'update';

        let url = `/hydroshare/${siteCode}/${method}/`;
        let serializedForm = $(hydroshareSettingsForm).serialize();
        let progressSpinner = $(hydroshareSettingsForm).find('#hs-progress-spinner');

        for (let spinner of progressSpinner)
            componentHandler.upgradeElement(spinner);

        progressSpinner.addClass('is-active');
        $('span#hs-loading-msg').prop('hidden', false);

        $.post(url, serializedForm)
            .done(data => {
                console.log(data);
                if (data.redirect)
                    window.location.href = data.redirect;
                else
                    dialog.close();
            }).fail((xhr) => {
                if (xhr.responseJSON) {
                    let errors = xhr.responseJSON;

                    console.error(xhr.responseJSON);

                    if (xhr.status == 500 && errors.error) {
                        let errorContainer = $('div#err-msg-container').find('p');
                        $(errorContainer).html(errors.error);
                    }

                    for (let [errorName, errorList] of Object.entries(errors)) {
                        if (Array.isArray(errorList)) {
                            let fieldContainer = $(`#id_${errorName}`);
                            let errorContainer = $(fieldContainer).find('ul.errorlist');

                            if (errorContainer.length) {
                                $(errorContainer).html('');
                            } else {
                                $(fieldContainer).prepend(`<ul class="errorlist"></ul>`);
                                errorContainer = $(fieldContainer).find('ul.errorlist');
                            }

                            for (let err of errorList) {
                                $(errorContainer).append(`<li>${err}</li>`);
                            }
                        }
                    }
                } else {
                    console.error(xhr.responseText);
                }
            }).always(() => {
                progressSpinner.removeClass('is-active');
                $('span#hs-loading-msg').prop('hidden', true);
                $(dialogButtons).prop('disabled', false);
                $(submitButton).addClass('mdl-button--colored');
            });
    }
}
