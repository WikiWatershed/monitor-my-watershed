/*
* hs-update-resource.js
* This script is loaded into the browser at /site/:sampling_feature_code/ when a user has a hydroshare account and
* they have started sharing data with hydroshare.org.
*
* The script makes an ajax request to the server to grab the page content used to manage hydroshare-sharing settings
* and loads the page content into the DOM.
* */
'use strict';

var siteCode = $('#site-code').val().trim();
const resource_template_url = `/hydroshare/${siteCode}/update/`;
const hydroshareContainer = $('#hydroshare-settings-container');

// Make a GET request to fetch HTML for hydroshare settings modal
$(hydroshareContainer).load(resource_template_url, () => {
    const updateNowButton = $('button#update-now-button');
    const hydroshareSettingsForm = $('#hydroshare-settings-form');
    const hydroshareError = $('p#hydroshare-error');

    initializeHydroShareSettingsDialog(); // called from `settings-form-dialog.js`
    initializeHydroShareDeleteDialog(); // called from `hs-delete-resource.js`

    /*
    * @desc - tells the server to update hydroshare resource files using latest site data
    * */
    $(updateNowButton).click(() => {
        $(updateNowButton).prop('disabled', true);
        $('p#hydroshare-error').text('');

        const url = `/hydroshare/${siteCode}/update/`;
        const serializedForm = $(hydroshareSettingsForm).serialize();
        const spinners = $('div[id=hs-progress-spinner]');

        for (let el of spinners)
            componentHandler.upgradeElement(el); // reinitializes MDL component so it actually works.

        $(spinners).addClass('is-active');

        // make POST request to upload site data files to hydroshare resource.
        $.post(url, `${serializedForm}&update_files=true`)
            .done((data) => {
                console.log(data);
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            })
            .fail((xhr) => {
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    $(hydroshareError).text(xhr.responseJSON.error);
                } else {
                    console.error("ERROR: ", xhr);
                    $(hydroshareError).text(xhr.statusText);
                }

            })
            .always(() => {
                $(spinners).removeClass('is-active');
                $(updateNowButton).prop('disabled', false);
            });
    });
});
