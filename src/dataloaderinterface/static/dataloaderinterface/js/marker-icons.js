/**
 * Created by Mauriel on 10/8/2018.
 */
var legendCollapsed = localStorage.getItem("legendCollapsed");
legendCollapsed = legendCollapsed == null ? "show" : legendCollapsed;

console.log(legendCollapsed);
function getMarkerIcons() {
    var skinnyIcons = {
        blue: {
            url: "/static/dataloaderinterface/images/marker-blue-skinny-bright.png",
            size: new google.maps.Size(36, 63),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 58),
            scaledSize: new google.maps.Size(36, 63)
        },
        green: {
            url: "/static/dataloaderinterface/images/marker-green-skinny-bright.png",
            size: new google.maps.Size(36, 63),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 58),
            scaledSize: new google.maps.Size(36, 63)
        },
        orange: {
            url: "/static/dataloaderinterface/images/marker-orange-skinny-bright.png",
            size: new google.maps.Size(36, 63),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 58),
            scaledSize: new google.maps.Size(36, 63)
        },
        red: {
            url: "/static/dataloaderinterface/images/marker-red-skinny-bright.png",
            size: new google.maps.Size(36, 63),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 58),
            scaledSize: new google.maps.Size(36, 63)
        },
        yellow: {
            url: "/static/dataloaderinterface/images/marker-yellow-skinny-bright.png",
            size: new google.maps.Size(36, 63),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 58),
            scaledSize: new google.maps.Size(36, 63)
        },
        darkgreen: {
            url: "/static/dataloaderinterface/images/marker-darkgreen-skinny-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        lightgreen: {
            url: "/static/dataloaderinterface/images/marker-lightgreen-skinny-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        }
    };

    var fatIcons = {
        blue: {
            url: "/static/dataloaderinterface/images/marker-blue-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        green: {
            url: "/static/dataloaderinterface/images/marker-green-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        orange: {
            url: "/static/dataloaderinterface/images/marker-orange-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        red: {
            url: "/static/dataloaderinterface/images/marker-red-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        yellow: {
            url: "/static/dataloaderinterface/images/marker-yellow-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        darkgreen: {
            url: "/static/dataloaderinterface/images/marker-darkgreen-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        },
        lightgreen: {
            url: "/static/dataloaderinterface/images/marker-lightgreen-fat-bright.png",
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        }
    };

    return {skinny: skinnyIcons, fat: fatIcons}
}

function appendLegend(map) {
    // Append legend:
    var legendDiv = document.createElement('div');

    // Set CSS for the control border.
    var legendUI = document.createElement('div');
    legendUI.classList.add("mapControlUI");
    legendUI.style.maxWidth = "190px";
    legendUI.style.fontSize = "12px";
    legendDiv.appendChild(legendUI);

    // Set CSS for the control interior.
    var legendText = document.createElement('div');
    legendText.style.padding = "1em";
    legendText.innerHTML = `
        <strong data-toggle="collapse" href="#legendCollapse" class="${legendCollapsed == "show"?"collapsed":""}""
            aria-expanded="${legendCollapsed == "show"?"true":"false"}" aria-controls="legendCollapse"
            style="cursor: pointer;">
            <i class="material-icons icon-arrow" style="vertical-align: middle;">keyboard_arrow_down</i>
            <span style="vertical-align: middle;">Legend</span>
        </strong>
        <div class="collapse ${legendCollapsed}" id="legendCollapse">
            <hr>
            <p style="font-size: 12px;">Data Age:</p>
            <table class="legend-table">
                <tbody>
                    <tr>
                        <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-darkgreen-fat-bright.png" 
                        alt="Marker for data within last 6 hours"></td>
                        <td>Has data within the last 6 hours</td>
                    </tr>
                    <tr>
                        <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-lightgreen-fat-bright.png" 
                        alt="Marker for data within last 72 hours"></td>
                        <td>Has data within the last 72 hours</td>
                    </tr>
                    <tr>
                        <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-yellow-fat-bright.png" 
                        alt="Marker for data within last 2 weeks"></td>
                        <td>Has data within the last 2 weeks</td>
                    </tr>
                    <tr>
                        <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-red-fat-bright.png" 
                        alt="Marker for data out of date"></td>
                        <td>Out of date</td>
                    </tr>
                </tbody>
            </table>
            <br>
            <p style="font-size: 12px;">Ownership:</p>
            <table class="legend-table">
                <tr>
                    <td>
                        <img class="legend-marker" src="/static/dataloaderinterface/images/marker-darkgreen-skinny-bright.png" 
                        alt="Marker for sites you own">
                    </td>
                    <td>Sites you own</td>
                </tr>
                <tr>
                    <td>
                        <img class="legend-marker" src="/static/dataloaderinterface/images/marker-darkgreen-fat-bright.png" 
                        alt="Marker for sites you do not own">
                    </td>
                    <td>Sites you do not own</td>
                </tr>
            </table>
        </div>`;

    legendUI.appendChild(legendText);
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(legendDiv);
}

$(document).ready(function () {
    $(".map-container").on("click", "[href='#legendCollapse']", function () {
        var collapse = $(this).parent().find(".collapse");
        localStorage.setItem("legendCollapsed", !collapse.hasClass("show") ? "show" : "");
    });
});
