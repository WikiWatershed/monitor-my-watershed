var markers = [];
var map;
var filters = {
    dataTypes: {
        key: 'dataType',
        icon: 'cloud_queue',
        label: 'Data Types',
        values: {},
        inclusive: true, // For filter items that can take multiple values from a set of values
        has_search: false
    },
    organizations: {
        key: 'organization',
        label: 'Organizations',
        icon: 'business',   // From https://material.io/icons/
        values: {},
        has_search: true
    },
    siteTypes: {
        key: 'type',
        icon: 'layers',
        label: 'Site Types',
        values: {},
        has_search: true
    }
};

function initMap() {
    const DEFAULT_ZOOM = 5;
    const DEFAULT_SPECIFIC_ZOOM = 12;
    const DEFAULT_LATITUDE = 40.0902;
    const DEFAULT_LONGITUDE = -95.7129;
    const DEFAULT_POSITION = { lat: DEFAULT_LATITUDE, lng: DEFAULT_LONGITUDE };
    var ZOOM_LEVEL = sessionStorage && parseInt(sessionStorage.getItem('CURRENT_ZOOM')) || DEFAULT_ZOOM;
    var temp = sessionStorage.getItem('CURRENT_CENTER');
    var MAP_CENTER = DEFAULT_POSITION;

    if(sessionStorage.getItem('CURRENT_CENTER')) {
        MAP_CENTER = getLatLngFromString(temp);
    } else if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function getLocation(locatedPosition) {
            map.setCenter({ lat: locatedPosition.coords.latitude, lng: locatedPosition.coords.longitude });
            map.setZoom(DEFAULT_SPECIFIC_ZOOM);
        }, undefined, { timeout: 5000 });
    }

    var markerData = JSON.parse(document.getElementById('sites-data').innerHTML);

    map = new google.maps.Map(document.getElementById('map'), {
        center: MAP_CENTER,
        zoom: ZOOM_LEVEL,
        gestureHandling: 'greedy',
        zoomControl: true,
        zoomControlOptions: {
            position: google.maps.ControlPosition.LEFT_BOTTOM
        },
        mapTypeId: google.maps.MapTypeId.TERRAIN,
        scaleControl: true
    });

    map.setOptions({minZoom: 1, maxZoom: 18});

    var infoWindow = new google.maps.InfoWindow({
        content: ''
    });

    map.addListener('zoom_changed', function(){
        var CURRENT_ZOOM = map.getZoom();
        sessionStorage.setItem('CURRENT_ZOOM', CURRENT_ZOOM);
    });

    map.addListener('center_changed', function(){
        var CURRENT_CENTER = map.getCenter();
        sessionStorage.setItem('CURRENT_CENTER', CURRENT_CENTER);
    });

    var infoWindow = new google.maps.InfoWindow({
        content: ''
    });

    var prevMarker;
    var prevZIndex;

    markerData.forEach(function(site) {
        var marker = new google.maps.Marker({
            position: {lat: site.latitude, lng: site.longitude},
            map: map,
            icon: getMarkerIcon(site.status, site.dataAge, site.dataType.split(",")),
            title: site.name
        });

        for (var f in filters) {
            marker[filters[f].key] = site[filters[f].key];
        }

        marker.addListener('click', function () {
            if (prevMarker) {
                prevMarker.setZIndex(prevZIndex);
            }

            prevMarker = this;
            prevZIndex = this.zIndex;

            var infoContent = createInfoWindowContent(site);
            infoWindow.setContent(infoContent);
            infoWindow.open(marker.get('map'), marker);

            marker.setZIndex(google.maps.Marker.MAX_ZINDEX + 1); // Bring the marker to the front
        });

        markers.push(marker);
    });

    appendLegend(map);
    appendExtraUI();
}

function appendExtraUI() {
    // Append division for showing number of results:
    var resultsDiv = document.createElement('div');

    // Set CSS for the control border.
    var resultslUI = document.createElement('div');
    resultslUI.classList.add("mapControlUI");
    resultslUI.style.width = "250px";
    resultslUI.style.fontSize = "14px";
    resultsDiv.appendChild(resultslUI);

    // Set CSS for the control interior.
    var controlText = document.createElement('div');
    controlText.style.padding = "1em";
    controlText.innerHTML = 'Showing <strong id="marker-count">'
        + markers.length + '</strong> out of <strong id="marker-total-count">'
        + markers.length + '</strong> results.';
    resultslUI.appendChild(controlText);

    map.controls[google.maps.ControlPosition.BOTTOM_CENTER].push(resultsDiv);
}

$(document).ready(function () {
    $('nav .menu-browse-sites').addClass('active');
    resizeContent();

    var markerData = JSON.parse(document.getElementById('sites-data').innerHTML);

    markerData.forEach(function (site) {
        for (var f in filters) {
            var keys = [site[filters[f].key]];
            if (filters[f].inclusive) {
                keys = [];
                var includes = site[filters[f].key].split(",");
                for (var i = 0; i < includes.length; i++) {
                    if (includes[i].trim()) {
                        keys.push(includes[i].trim());
                    }
                }
            }
            for (var ckey in keys) {
                if (filters[f].values[keys[ckey]])
                    filters[f].values[keys[ckey]] += 1;
                else
                    filters[f].values[keys[ckey]] = 1;    // Initialize count
            }
        }
    });

    // Move the items to an array so we can sort them
    for (var f in filters) {
        filters[f].values_sortable = [];
        for (var val in filters[f].values) {
            filters[f].values_sortable.push([val, filters[f].values[val]]);
        }
    }

    // Sort the arrays alphabetically
    for (var f in filters) {
        filters[f].values_sortable.sort(function (a, b) {
            return b[0] > a[0] ? -1 : 1;
        });
    }

    // Append filter headers
    for (var f in filters) {
        $("#filters").append('<div class="filter-container"><div class="filter-header">\
                    <table class="mdl-data-table mdl-js-data-table mdl-data-table--selectable mdl-shadow--2dp full-width">\
                        <tr>\
                            <td class="mdl-data-table__cell--non-numeric">\
                                <a data-toggle="collapse" href="#collapse-' + filters[f].key + '" role="button" aria-expanded="true"\
                                   aria-controls="collapse-' + f.key + '" style="text-decoration: none; color: #222;">\
                                    <h6><i class="material-icons mdl-shadow--2dp">' + filters[f].icon + '</i> ' + filters[f].label + '<i class="material-icons icon-arrow pull-right">keyboard_arrow_down</i></h6>\
                                </a>\
                            </td>\
                        </tr>\
                    </table>\
                </div>\
                <div id="collapse-' + filters[f].key + '" class="show filter-body" data-facet="' + filters[f].key + '">\
                    <table class="mdl-data-table mdl-js-data-table mdl-data-table--selectable mdl-shadow--2dp full-width">\
                        <tbody>'+ (filters[f].has_search ?
                            '<tr class="td-filter">\
                                <td class="mdl-data-table__cell--non-numeric">\
                                    <div class="input-group">\
                                        <span class="input-group-addon" id="basic-addon1"><i class="material-icons">search</i></span>\
                                        <input type="text" class="form-control input-filter" placeholder="Search ' + filters[f].label + '...">\
                                    </div>\
                                </td>\
                            </tr>':'')+
                        '</tbody>\
                    </table>\
                </div></div>'
        );

        // Append filter items
        for (var item = 0; item < filters[f].values_sortable.length; item++) {
            $("#collapse-" + filters[f].key + " > table tbody").append(' <tr>\
                <td class="mdl-data-table__cell--non-numeric">\
                    <label class="mdl-checkbox mdl-js-checkbox mdl-js-ripple-effect" for="chk-' + filters[f].key + '-' + filters[f].values_sortable[item][0] + '">\
                        <input type="checkbox" id="chk-' + filters[f].key + '-' + filters[f].values_sortable[item][0] + '"\
                        class="mdl-checkbox__input chk-filter" data-value="'+ filters[f].values_sortable[item][0] + '">\
                        <span class="mdl-checkbox__label">' + filters[f].values_sortable[item][0] + '</span>\
                    </label>\
                    <span class="badge badge-info">' + filters[f].values_sortable[item][1] + '</span>\
                </td>\
            </tr>');
        }
    }

    // Bind search events
    $(".input-filter").keyup(function() {
        var items = $(this).closest("tbody").find("tr:not(.td-filter)");
        var searchStr = $(this).val().trim().toUpperCase();

        if (searchStr.length > 0) {
            items.hide();

            var results = items.filter(function () {
                return $(this).find('label').text().trim().toUpperCase().indexOf(searchStr) >= 0;
            });

            results.show();
        }
        else {
            items.show();
        }
    });

    $("#btnClearFilters").click(function () {
        // document.querySelector('.chk-filter').parentElement.MaterialCheckbox.uncheck();
        var items = $(".chk-filter");
        for (var i = 0; i < items.length; i++) {
            $(items[i]).parent()[0].MaterialCheckbox.uncheck();
        }
        for (var i = 0; i < markers.length; i++) {
            markers[i].setVisible(true);
        }

        if ($("#switch-zoom").prop("checked")) {
            zoomExtent();
        }

        $("#marker-count").text(markers.length);
        $("#marker-total-count").text(markers.length);
    });

    $("#switch-zoom").change(function () {
        if ($(this).prop("checked")) {
            zoomExtent();
        }
    });

    $(".chk-filter").change(function() {
        var checkedItems = getCurrentFilters();
        var someVisible = false;
        var count = 0;

        // If nothing selected, display all
        if (!checkedItems.length) {
            for (var i = 0; i < markers.length; i++) {
                markers[i].setVisible(true);
            }
            someVisible = true;
            count = markers.length;
        }
        else {
            for (var i = 0; i < markers.length; i++) {
                var visible = true;    // Starts as true by default
                for (var j = 0; j < checkedItems.length; j++) {
                    var key = checkedItems[j][0];
                    var values = checkedItems[j][1];

                    var isInclusive = false;
                    for (var f in filters) {
                        if (filters[f].key == key && filters[f].inclusive) {
                            isInclusive = true;
                            break;
                        }
                    }

                    if (isInclusive) {
                        var ckey = markers[i][key].split(",");
                        var found = false;
                        for (var v in ckey) {
                            if (ckey[v] && !(values.indexOf(ckey[v]) < 0)) {
                                found = true;
                                break;
                            }
                        }
                        visible = visible && found; // Hide if none of the values were filtered
                    }
                    else {
                        if (values.indexOf(markers[i][key]) < 0) {
                            visible = false; // Hide if not included in some filter
                        }
                    }
                }

                if (visible) {
                    count++;
                    someVisible = true;
                }

                markers[i].setVisible(visible);

                someVisible = someVisible || (!someVisible && visible)
            }
        }

        // Populate map count
        $("#marker-count").text(count);
        $("#marker-total-count").text(markers.length);

        if ($("#switch-zoom").prop("checked") && someVisible) {
            zoomExtent();
        }
    });
});

// Zooms to the extent of markers.
function zoomExtent() {
    var bounds = new google.maps.LatLngBounds();
    for (var i = 0; i < markers.length; i++) {
        if (markers[i].visible) {
            bounds.extend(markers[i].getPosition());
        }
    }

    map.fitBounds(bounds);
}

// Returns an object listing currently checked filter items
function getCurrentFilters() {
    var filters = $(".filter-body");
    var results = [];

    for (var i = 0; i < filters.length; i++) {
        var items = [];
        var checked = $(filters[i]).find(".chk-filter:checked");

        for (var j = 0; j < checked.length; j++) {
            items.push($(checked[j]).attr("data-value"));
        }

        if (items && items.length > 0) {
            var facet = $(filters[i]).attr("data-facet");
            results.push([facet, items]);
        }
    }

    return results;
}

$(window).resize(resizeContent);

function resizeContent() {
    $(".map-container").css("height", $("#wrapper").height() - $("#title-row").height());
    $("#filters-row").css("height", $("#wrapper").height() - $("#title-row").height());
}

function getLatLngFromString(location) {
    var latlang = location.replace(/[()]/g,'');
    var latlng = latlang.split(',');
    var locate = new google.maps.LatLng(parseFloat(latlng[0]) , parseFloat(latlng[1]));
    return locate;
}