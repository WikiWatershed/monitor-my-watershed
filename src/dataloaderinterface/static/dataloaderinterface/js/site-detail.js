const EXTENT_HOURS = 72;
const GAP_HOURS = 6;
const STALE_DATA_CUTOFF = new Date(new Date() - 1000 * 60 * 60 * EXTENT_HOURS);

function initMap() {
    var defaultZoomLevel = 18;
    var latitude = parseFloat($('#site-latitude').val());
    var longitude = parseFloat($('#site-longitude').val());
    var sitePosition = {lat: latitude, lng: longitude};

    var map = new google.maps.Map(document.getElementById('map'), {
        center: sitePosition,
        gestureHandling: 'greedy',
        zoom: defaultZoomLevel,
        mapTypeId: google.maps.MapTypeId.HYBRID
    });

    map.setOptions({minZoom: 3, maxZoom: 18});

    var marker = new google.maps.Marker({
        position: sitePosition,
        map: map
    });
}

function fillValueTable(table, data) {
    var rows = data.map(function (dataValue) {
        return "<tr><td class='mdl-data-table__cell--non-numeric'>" + dataValue.DateTime + "</td><td class='mdl-data-table__cell--non-numeric'>" + dataValue.TimeOffset + "</td><td>" + dataValue.Value + "</td></tr>";
    });
    table.append($(rows.join('')));
}

function drawSparklineOnResize(seriesInfo, seriesData) {
    var resizeTimer;
    window.addEventListener('resize', function (event) {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            drawSparklinePlot(seriesInfo, seriesData);
        }, 500);
    });
}

function drawSparklinePlot(seriesInfo, seriesData) {
    var card = $('div.plot_box[data-result-id="' + seriesInfo['resultId'] + '"]');
    var plotBox = card.find(".graph-container");

    plotBox.empty();

    var margin = {top: 5, right: 1, bottom: 5, left: 1};
    var width = plotBox.width() - margin.left - margin.right;
    var height = plotBox.height() - margin.top - margin.bottom;

    if (seriesData.length === 0) {
        card.find(".table-trigger").toggleClass("disabled", true);
        card.find(".download-trigger").toggleClass("disabled", true);
        card.find(".tsa-trigger").toggleClass("disabled", true);

        // Append message when there is no data
        d3.select(plotBox.get(0)).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("text")
                .text("No data exist for this variable.")
                .attr("font-size", "12px")
                .attr("fill", "#AAA")
                .attr("text-anchor", "left")
                .attr("transform", "translate(" + (margin.left + 10) + "," + (margin.top + 20) + ")");
        return;
    }

    var lastRead = Math.max.apply(Math, seriesData.map(function(value){
        return new Date(value.DateTime);
    }));

    var dataTimeOffset = Math.min.apply(Math, seriesData.map(function(value){
        return new Date(value.DateTime);
    }));

    var xAxis = d3.scaleTime().range([0, width]);
    var yAxis = d3.scaleLinear().range([height, 0]);

    var yDomain = d3.extent(seriesData, function(d) {
        return parseFloat(d.Value);
    });
    var yPadding = (yDomain[1] - yDomain[0]) / 20;  // 5% padding
    yDomain[0] -= yPadding;
    yDomain[1] += yPadding;

    xAxis.domain([dataTimeOffset, lastRead]);
    yAxis.domain(yDomain);

    var line = d3.line()
        .x(function(d) {
            var date = new Date(d.DateTime);
            return xAxis(date);
        })
        .y(function(d) {
            return yAxis(d.Value);
        });

    var svg = d3.select(plotBox.get(0)).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("class", function() {
            if (lastRead <= STALE_DATA_CUTOFF) {
                return "stale";
            }

            return "not-stale";
        })
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // Rendering the paths
    var gapOffset;  // The minimum date required before being considered a gap.
    var previousDate;
    var start = 0;  // Latest start detected after a gap. Initially set to the start of the list.
    var paths = [];

    for (var i = 0; i < seriesData.length; i++) {
        var currentDate = new Date(seriesData[i].DateTime);

        if (previousDate) {
            gapOffset = new Date(currentDate - 1000 * 60 * 60 * GAP_HOURS);
        }

        if (previousDate && previousDate < gapOffset) {
            paths.push(seriesData.slice(start, i));
            start = i;
        }
        previousDate = currentDate;
    }

    if (start > 0) {
        paths.push(seriesData.slice(start, seriesData.length));
    }
    else {
        paths.push(seriesData); // No gaps were detected. Just plot the entire original data.
    }

    // Plot all paths separately to display gaps between them.
    for (var i = 0; i < paths.length; i++) {
        if (paths[i].length == 1) {
            svg.append("circle")
                .attr("r", 2)
                .style("fill", "steelblue")
                .attr("transform", "translate(" + xAxis(new Date(paths[i][0].DateTime)) + ", " + yAxis(paths[i][0].Value) + ")")
        }
        else {
            svg.append("path")
            .data([paths[i]])
            .attr("class", "line").attr("d", line)
            .attr("stroke", "steelblue");
        }
    }
}

function getTimeSeriesData(sensorInfo) {
    if (sensorInfo['influxUrl'] === 'None' ) { return; }
    $.ajax({
        url: sensorInfo['influxUrl']
    }).done(function(influx_data) {
        var resultSet = influx_data.results ? influx_data.results.shift() : null;
        if (resultSet && resultSet.series && resultSet.series.length) {
            var influxSeries = resultSet.series.shift();
            var indexes = {
                time: influxSeries.columns.indexOf("time"),
                value: influxSeries.columns.indexOf("DataValue"),
                offset: influxSeries.columns.indexOf("UTCOffset")
            };
            var values = influxSeries.values.map(function(influxValue) {
                return {
                    DateTime: influxValue[indexes.time].match(/^(\d{4}\-\d\d\-\d\d([tT][\d:]*)?)/).shift(),
                    Value: influxValue[indexes.value],
                    TimeOffset: influxValue[indexes.offset]
                }
            });

            fillValueTable($('table.data-values[data-result-id=' + sensorInfo['resultId'] + ']'), values);
            drawSparklineOnResize(sensorInfo, values);
            drawSparklinePlot(sensorInfo, values);
        } else {
            console.log('No data values were found for this site');
            drawSparklinePlot(sensorInfo, []);  // Will just render the empty message
            // console.info(series.getdatainflux);
        }
    }).fail(function() {
        drawSparklinePlot(sensorInfo, []);  // Will just render the empty message
        console.log('data failed to load.');
    });
}

$(document).ready(function () {
    var dialog = $('#data-table-dialog');
    $("#chkFollow").on("change", function () {
        var statusContainer = $(".follow-status");
        var followForm = $("#follow-site-form");
        var following = !$(this).prop("checked");

        $.ajax({
            url: $('#follow-site-api').val(),
            type: 'post',
            data: {
                csrfmiddlewaretoken: followForm.find('input[name="csrfmiddlewaretoken"]').val(),
                sampling_feature_code: followForm.find('input[name="sampling_feature_code"]').val(),
                action: (following) ? 'unfollow' : 'follow'
            }
        }).done(function () {
            statusContainer.toggleClass("following");
            var message = !following ? 'You are now following this site.' : 'This site has been unfollowed.';
            snackbarMsg(message);
        });
    });

    $(".table-trigger").click(function () {
        var box = $(this).parents('.plot_box');
        var id = box.data('result-id');
        var tables = $('table.data-values');
        tables.hide();

        tables.filter('[data-result-id="' + id + '"]').show();
        var title = box.data('variable-name') + ' (' + box.data('variable-code') + ')';
        dialog.find('.mdl-dialog__title').text(title);
        dialog.find('.mdl-dialog__title').attr("title", title);

        dialog.modal('show');
    });

    $('nav .menu-sites-list').addClass('active');

    var sensors = document.querySelectorAll('.sparkline-plots .plot_box');
    for (var index = 0; index < sensors.length; index++) {
        var sensorInfo = sensors[index].dataset;
        getTimeSeriesData(sensorInfo);
    }

    $("#id_data_file").change(function() {
        $(".selected-file > span").text(this.files[0].name);
        $(".selected-file").show();
        $("#file-preview-default").hide();
        $("#btn-upload-file").prop("disabled", false);
    });

    $("#btn-upload-file").click(function () {
        var form = $("#form-file-upload"),
            formData = new FormData(),
            formParams = form.serializeArray();

        var file = $("#id_data_file")[0].files[0];
        formData.append("data_file", file);

        $.each(formParams, function (i, val) {
            formData.append(val.name, val.value);
        });

        var url = form.attr("action");

        // Change text to Uploading...
        $("#btn-upload-file").prop("disabled", true);
        $("#btn-upload-file").find("span").text("Uploading...");

        $.ajax({
            url: url,
            type: "POST",
            data: formData,
            // xhr: function () {
            //     var myXhr = $.ajaxSettings.xhr();
            //     if (myXhr.upload) {
            //
            //     }
            //     return myXhr;
            // },
        }).done(function (response) {
            console.log(response);
        }).fail(function (error) {
            console.log(error);
        }).always(function () {
            // Restore state
            $("#btn-upload-file").prop("disabled", false);
            $("#btn-upload-file").find("span").text("Upload");
        });
    });
});
