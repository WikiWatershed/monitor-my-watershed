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

    var map = new google.maps.Map(document.getElementById('map'), {
        center: MAP_CENTER,
        zoom: ZOOM_LEVEL,
        gestureHandling: 'greedy',
        zoomControl: true,
        zoomControlOptions: {
            position: google.maps.ControlPosition.LEFT_BOTTOM
        },
        mapTypeId: google.maps.MapTypeId.HYBRID,
        scaleControl: true
    });

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


    markerData.forEach(function(site) {
        var marker = new google.maps.Marker({
            position: { lat: site.latitude, lng: site.longitude },
            map: map
        });

        marker.addListener('click', function() {
            var contentElement = $('<div></div>').append($('#site-marker-content').html());
            var fields = contentElement.find('.site-field');
            fields.each(function(index, element) {
                var field = $(element).data('field');
                $(element).find('.site-data').text(site[field]);
            });
            contentElement.find('.site-link a').attr('href', site.detail_link);

            var infoContent = $('<div></div>').append(contentElement.html()).html();
            infoWindow.setContent(infoContent);
            infoWindow.open(marker.get('map'), marker);
        });
    });
}

$(document).ready(function () {
    $('nav .menu-browse-sites').addClass('active');

    $("#wrapper").css("height", "calc(100% - 81px)");
    $(".map-container").css("height", $("#wrapper").height());
    $("body").css("overflow", "hidden")
});

$( window ).resize(function() {
  $(".map-container").css("height", $("#wrapper").height());
    $("body").css("overflow", "hidden")
});

function getLatLngFromString(location) {
    var latlang = location.replace(/[()]/g,'');
    var latlng = latlang.split(',');
    var locate = new google.maps.LatLng(parseFloat(latlng[0]) , parseFloat(latlng[1]));
    return locate;
}