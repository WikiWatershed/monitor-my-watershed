/**
 * Created by Mauriel on 1/19/2018.
 */

$(document).on('click', ".mdl-chip__action.action_cancel", function () {
    $(this).closest(".message-container").remove();
});

$(document).on('change', "#switch-zoom", function () {
    localStorage.setItem("AutoZoom", JSON.stringify($(this).prop("checked")));
});

$(document).on('click', ".menu-order li", function () {
    var target = $(this).parent()[0].dataset.sortTarget;

    if ($(this).attr("data-sort-by")) {
        $(this).parent().find("li[data-sort-by]").removeClass("active");
        $(this).addClass("active");
    }
    else {
        $(this).parent().find("li[data-order]").removeClass("active");
        $(this).addClass("active");
    }

    var sortBy = $(this).parent().find("li[data-sort-by].active").attr("data-sort-by");
    var order = $(this).parent().find("li[data-order].active").attr("data-order");

    $(target + ' .sortable').sort(function (a, b) {
        if (order == "asc") {
            return (a.dataset[sortBy].toUpperCase() > b.dataset[sortBy].toUpperCase());
        }

        return (a.dataset[sortBy].toUpperCase() < b.dataset[sortBy].toUpperCase());
    }).appendTo(target);

    var UISortState = JSON.parse(localStorage.getItem("UISortState")) || {};
    UISortState[target] = {sortBy: sortBy, order: order};

    localStorage.setItem("UISortState", JSON.stringify(UISortState));
});

function snackbarMsg(message, duration = 3000) {
    var snackbarContainer = document.querySelector('#clipboard-snackbar');
    snackbarContainer.MaterialSnackbar.showSnackbar({
        message: message,
        timeout: duration
    });
}

// Taken from https://stackoverflow.com/questions/15900485/correct-way-to-convert-size-in-bytes-to-kb-mb-gb-in-javascript
function formatBytes(bytes, decimals) {
    if (bytes == 0) return '0 Bytes';
    var k = 1024,
        dm = decimals || 2,
        sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
        i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

$(document).ready(function () {
    var UISortState = JSON.parse(localStorage.getItem("UISortState")) || {};

    // Set state read from local storage
    for (var item in UISortState) {
        var sortBy = UISortState[item].sortBy;
        var order = UISortState[item].order;

        var ul = $("ul[data-sort-target='" + item + "']");
        ul.find("[data-sort-by='" + sortBy + "']").addClass("active");
        ul.find("[data-order='" + order + "']").addClass("active");

        $(item + ' .sortable').sort(function (a, b) {
            if (order == "asc") {
                return (a.dataset[sortBy] > b.dataset[sortBy]);
            }

            return (a.dataset[sortBy] < b.dataset[sortBy]);
        }).appendTo(item);

        $(item).addClass("sorted");
    }

    // Sort anything not already sorted alphabetically and ascending
    var instances = $("ul[data-sort-target]");

    for (var i = 0; i < instances.length; i++) {
        var target = $(instances[i]).attr("data-sort-target");
        if (!$(target).hasClass("sorted")) {
            var sortBy = "sitecode";
            var order = "asc";

            var ul = $("ul[data-sort-target='" + target + "']");
            ul.find("[data-sort-by='" + sortBy + "']").addClass("active");
            ul.find("[data-order='" + order + "']").addClass("active");

            $(target + ' .sortable').sort(function (a, b) {
                if (order == "asc") {
                    return (a.dataset[sortBy] > b.dataset[sortBy]);
                }

                return (a.dataset[sortBy] < b.dataset[sortBy]);
            }).appendTo(target);

            $(target).addClass("sorted");
        }
    }

    // Populate footer's release version
    $.ajax({
        url: "https://api.github.com/repos/ODM2/ODM2DataSharingPortal/releases"
    }).done(function (response) {
        var tagName = response[0].tag_name.replace("v", "Version ");
        var URL = response[0].html_url;
        $("#txtRelease").attr("href", URL).text(tagName);
    });

    // Set auto zoom status
    if (localStorage.getItem("AutoZoom") != null) {
        var autoZoomStatus = JSON.parse(localStorage.getItem("AutoZoom"));
        $("#switch-zoom").prop("checked", autoZoomStatus)
    }
});