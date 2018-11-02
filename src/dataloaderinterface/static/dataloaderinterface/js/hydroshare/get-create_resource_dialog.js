/*
 * hs-create-resource.js
 * This script is loaded into the browser at /site/:sampling_feature_code/ when a user has a hydroshare account and
 * they have not started sharing data with hydroshare.org.
 *
 * The script makes an ajax request to the server to grab the page content used to start sharing site data with
 * HydroShare and loads the page content into the DOM.
 * */

$(() => {
    const siteCode = $('#site-code').val().trim();
    const template_url = `/hydroshare/${siteCode}/create/`;
    const hydroshareContainer = $('#hydroshare-settings-container');

    $.get(template_url)
        .done(data => {
            $(hydroshareContainer).html(data);
            initializeHydroShareSettingsDialog(); // called from `hydroshare-resource-modal.js`
        })
        .fail(xhr => {
            if (xhr.responseJSON) {
                console.error(xhr.responseJSON);
            } else {
                console.error(xhr.responseText);
            }
        })
});