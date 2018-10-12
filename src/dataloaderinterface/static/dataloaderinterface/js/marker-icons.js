/**
 * Created by Mauriel on 10/8/2018.
 */
var legendCollapsed = localStorage.getItem("legendCollapsed") == null ? "show" : localStorage.getItem("legendCollapsed");

function createInfoWindowContent(site) {
    var contentElement = $('<div></div>').append($('#site-marker-content').html());
    var fields = contentElement.find('.site-field');
    fields.each(function(index, element) {
        var field = $(element).data('field');
        $(element).find('.site-data').text(site[field]);
    });
    contentElement.find('.site-link a').attr('href', site.detail_link);

    return $('<div></div>').append(contentElement.html()).html();
}

function getMarkerIcon(type, color, dataTypes) {
    type = type != "owned" ? "fat" : "skinny";
    if (dataTypes[0] == "Leaf Pack") {
        color = "orangered";
    }
    var icon = {
        skinny: {
            size: new google.maps.Size(36, 63),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 58),
            scaledSize: new google.maps.Size(36, 63)
        },
        fat: {
            size: new google.maps.Size(36, 49),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(18, 44),
            scaledSize: new google.maps.Size(36, 49)
        }
    };

    icon[type].url = "/static/dataloaderinterface/images/marker-" + color + "-" + type + "-bright.png";
    return icon[type];
}

function appendLegend(map) {
    // Append legend:
    var legendDiv = document.createElement('div');

    // Set CSS for the control border.
    var legendUI = document.createElement('div');
    legendUI.classList.add("mapControlUI");
    legendUI.style.maxWidth = "300px";
    legendUI.style.fontSize = "12px";
    legendDiv.appendChild(legendUI);

    // Set CSS for the control interior.
    var legendText = document.createElement('div');
    legendText.style.padding = "1em";
    legendText.innerHTML = `
        <strong data-toggle="collapse" href="#legendCollapse" class="${legendCollapsed == "show"?"collapsed":""}""
            aria-expanded="${legendCollapsed == "show"?"true":"false"}" aria-controls="legendCollapse"
            style="cursor: pointer; display:block;">
            <i class="material-icons icon-arrow" style="vertical-align: middle;">keyboard_arrow_down</i>
            <span style="vertical-align: middle;">Legend</span>
        </strong>
        <div class="collapse ${legendCollapsed}" id="legendCollapse">
            <hr>
            <p class="title">Data Age:</p>
            <div class="flex">
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
                    </tbody>
                </table>
                <table class="legend-table">
                    <tbody>
                        <tr>
                            <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-red-fat-bright.png" 
                            alt="Marker for data out of date"></td>
                            <td>Sensor data out of date</td>
                        </tr>
                        <tr>
                            <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-gray-fat-bright.png" 
                            alt="Marker for sites with no data"></td>
                            <td>Sensors have no data</td>
                        </tr>
                        <tr>
                            <td><img class="legend-marker" src="/static/dataloaderinterface/images/marker-orangered-fat-bright.png" 
                            alt="Marker for sites with only Leaf Pack data"></td>
                            <td>Only Leaf Pack data</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <br>
            <p class="title">Ownership:</p>
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
