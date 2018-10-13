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
var textSearchFacets = ["code", "name", "organization", "type", "dataType"];

function initMap() {
    const DEFAULT_ZOOM = 5;
    const DEFAULT_SPECIFIC_ZOOM = 12;
    const DEFAULT_LATITUDE = 40.0902;
    const DEFAULT_LONGITUDE = -95.7129;
    const DEFAULT_POSITION = { lat: DEFAULT_LATITUDE, lng: DEFAULT_LONGITUDE };
    const ZOOM_LEVEL = sessionStorage && parseInt(sessionStorage.getItem('CURRENT_ZOOM')) || DEFAULT_ZOOM;
    const temp = sessionStorage.getItem('CURRENT_CENTER');
    let MAP_CENTER = DEFAULT_POSITION;

    if(sessionStorage.getItem('CURRENT_CENTER')) {
        MAP_CENTER = getLatLngFromString(temp);
    } else if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function getLocation(locatedPosition) {
            map.setCenter({ lat: locatedPosition.coords.latitude, lng: locatedPosition.coords.longitude });
            map.setZoom(DEFAULT_SPECIFIC_ZOOM);
        }, undefined, { timeout: 5000 });
    }

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

    map.addListener('zoom_changed', function(){
        let CURRENT_ZOOM = map.getZoom();
        sessionStorage.setItem('CURRENT_ZOOM', CURRENT_ZOOM);
    });

    map.addListener('center_changed', function(){
        let CURRENT_CENTER = map.getCenter();
        sessionStorage.setItem('CURRENT_CENTER', CURRENT_CENTER);
    });

    let infoWindow = new google.maps.InfoWindow({
        content: ''
    });

    let prevMarker;
    let prevZIndex;
    let markerData = JSON.parse(document.getElementById('sites-data').innerHTML);

    markerData.forEach(function(site) {
        let marker = new google.maps.Marker({
            position: {lat: site.latitude, lng: site.longitude},
            map: map,
            icon: getMarkerIcon(site.status, site.dataAge, site.dataType.split(",")),
            title: site.name,
            site: site
        });

        for (let f in filters) {
            marker[filters[f].key] = site[filters[f].key];
        }

        marker.addListener('click', function () {
            if (prevMarker) {
                prevMarker.setZIndex(prevZIndex);
            }

            prevMarker = this;
            prevZIndex = this.zIndex;

            let infoContent = createInfoWindowContent(site);
            infoWindow.setContent(infoContent);
            infoWindow.open(marker.get('map'), marker);

            marker.setZIndex(google.maps.Marker.MAX_ZINDEX + 1); // Bring the marker to the front
        });

        markers.push(marker);
    });

    appendMarkersLegend(map);
    appendResultsLegend();
    appendSearchControl();
}

function appendResultsLegend() {
    // Append division for showing number of results:
    let resultsDiv = document.createElement('div');

    // Set CSS for the control
    let resultslUI = document.createElement('div');
    resultslUI.classList.add("mapControlUI");
    resultslUI.style.width = "250px";
    resultslUI.style.fontSize = "14px";
    resultsDiv.appendChild(resultslUI);

    // Set CSS for the control interior.
    let controlText = document.createElement('div');
    controlText.style.padding = "1em";
    controlText.innerHTML = 'Showing <strong id="marker-count">'
        + markers.length + '</strong> out of <strong id="marker-total-count">'
        + markers.length + '</strong> results.';
    resultslUI.appendChild(controlText);

    map.controls[google.maps.ControlPosition.BOTTOM_CENTER].push(resultsDiv);
}

function appendSearchControl() {
    // Append division for search control:
    let searchDiv = document.createElement('div');

    // Set CSS for the control
    let searchUI = document.createElement('div');
    searchUI.style.fontSize = "14px";
    searchDiv.appendChild(searchUI);

    // Set CSS for the control interior.
    let controlText = document.createElement('div');
    controlText.classList.add("input-group");
    controlText.classList.add("search-wrapper");
    controlText.innerHTML = `
      <span class="input-group-addon" id="search-addon"><i class="material-icons">search</i></span>
      <input id="search" type="text" class="form-control" placeholder="Search sites..." aria-describedby="search-addon">
      <i id="search-clear" class="material-icons">cancel</i>
    `;
    searchUI.appendChild(controlText);

    map.controls[google.maps.ControlPosition.TOP_CENTER].push(searchDiv);
}

$(document).ready(function () {
    $('nav .menu-browse-sites').addClass('active');
    resizeContent();

    let markerData = JSON.parse(document.getElementById('sites-data').innerHTML);

    markerData.forEach(function (site) {
        for (let f in filters) {
            let keys = [site[filters[f].key]];
            if (filters[f].inclusive) {
                keys = [];
                let includes = site[filters[f].key].split(",");
                for (let i = 0; i < includes.length; i++) {
                    if (includes[i].trim()) {
                        keys.push(includes[i].trim());
                    }
                }
            }
            for (let ckey in keys) {
                if (filters[f].values[keys[ckey]])
                    filters[f].values[keys[ckey]] += 1;
                else
                    filters[f].values[keys[ckey]] = 1;    // Initialize count
            }
        }
    });

    // Move the items to an array so we can sort them
    for (let f in filters) {
        filters[f].values_sortable = [];
        for (let val in filters[f].values) {
            filters[f].values_sortable.push([val, filters[f].values[val]]);
        }
    }

    // Sort the arrays alphabetically
    for (let f in filters) {
        filters[f].values_sortable.sort(function (a, b) {
            return b[0] > a[0] ? -1 : 1;
        });
    }

    // Append filter headers
    for (let f in filters) {
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
        for (let item = 0; item < filters[f].values_sortable.length; item++) {
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

    // Bind search events for filter items
    $(".input-filter").keyup(function() {
        let items = $(this).closest("tbody").find("tr:not(.td-filter)");
        let searchStr = $(this).val().trim().toUpperCase();

        if (searchStr.length > 0) {
            items.hide();

            let results = items.filter(function () {
                return $(this).find('label').text().trim().toUpperCase().indexOf(searchStr) >= 0;
            });

            results.show();
        }
        else {
            items.show();
        }
    });

    // Bind search event for map control
    $(".map-container").on("keyup", "#search", filter);

    $(".map-container").on("click", "#search-clear", function () {
        $("#search").val("");
        filter();
    });

    $("#btnClearFilters").click(function () {
        // document.querySelector('.chk-filter').parentElement.MaterialCheckbox.uncheck();
        let items = $(".chk-filter");
        for (let i = 0; i < items.length; i++) {
            $(items[i]).parent()[0].MaterialCheckbox.uncheck();
        }
        for (let i = 0; i < markers.length; i++) {
            markers[i].setVisible(true);
        }

        if ($("#switch-zoom").prop("checked")) {
            zoomExtent();
        }

        $("#search").val("");
        $("#marker-count").text(markers.length);
        $("#marker-total-count").text(markers.length);
    });

    $("#switch-zoom").change(function () {
        if ($(this).prop("checked")) {
            zoomExtent();
        }
    });

    $(".chk-filter").change(filter);
});

function isSearched(metadata, searchString) {
    // Search each metadata element and see if it contains the search string
    for (let j = 0; j < textSearchFacets.length; j++) {
        if (metadata[textSearchFacets[j]].trim().toUpperCase().indexOf(searchString) >= 0) {
            return true;
        }
    }

    return false;
}

function filter() {
    let checkedItems = getCurrentFilters();
    let someVisible = false;
    let count = 0;
    const searchString = $("#search").val().trim().toUpperCase();

    // If no checkbox selected
    if (!checkedItems.length) {
        if (!searchString) {
            for (let i = 0; i < markers.length; i++) {
                markers[i].setVisible(true);
            }
            someVisible = true;
            count = markers.length;
        }
        else {
            for (let i = 0; i < markers.length; i++) {
                // Search each property and see if it contains the search string
                let visible = isSearched(markers[i].site, searchString);
                if (visible) {
                    someVisible = true;
                    count++;
                }

                markers[i].setVisible(visible);
            }
        }
    }
    else {
        for (let i = 0; i < markers.length; i++) {
            let visible = true;    // Starts as true by default
            for (let j = 0; j < checkedItems.length; j++) {
                let key = checkedItems[j][0];
                let values = checkedItems[j][1];
                let isInclusive = false;

                for (let f in filters) {
                    if (filters[f].key == key && filters[f].inclusive) {
                        isInclusive = true;
                        break;
                    }
                }

                if (isInclusive) {
                    let ckey = markers[i][key].split(",");
                    let found = false;
                    for (let v in ckey) {
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

            if (searchString) {
                visible = visible && isSearched(markers[i].site, searchString);
            }

            // Done filtering current marker

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
}

// Zooms to the extent of markers.
function zoomExtent() {
    let bounds = new google.maps.LatLngBounds();
    for (let i = 0; i < markers.length; i++) {
        if (markers[i].visible) {
            bounds.extend(markers[i].getPosition());
        }
    }

    map.fitBounds(bounds);
}

// Returns an object listing currently checked filter items
function getCurrentFilters() {
    let filters = $(".filter-body");
    let results = [];

    for (let i = 0; i < filters.length; i++) {
        let items = [];
        let checked = $(filters[i]).find(".chk-filter:checked");

        for (let j = 0; j < checked.length; j++) {
            items.push($(checked[j]).attr("data-value"));
        }

        if (items && items.length > 0) {
            let facet = $(filters[i]).attr("data-facet");
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
    let latlang = location.replace(/[()]/g,'');
    let latlng = latlang.split(',');
    return new google.maps.LatLng(parseFloat(latlng[0]) , parseFloat(latlng[1]));
}