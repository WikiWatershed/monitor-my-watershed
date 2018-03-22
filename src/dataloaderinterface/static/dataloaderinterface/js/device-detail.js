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
        mapTypeId: google.maps.MapTypeId.SATELLITE
    });

    var marker = new google.maps.Marker({
        position: sitePosition,
        map: map
    });
}

// Makes all site cards have the same height.
function fixViewPort() {
    var cards = $('.plot_box');

    var maxHeight = 0;
    for (var i = 0; i < cards.length; i++) {
        maxHeight = Math.max($(cards[i]).height(), maxHeight);
    }

    // set to new max height
    for (var i = 0; i < cards.length; i++) {
        $(cards[i]).height(maxHeight);
    }
}

function bindDeleteDialogEvents() {
    var deleteDialog = document.querySelector('#site-delete-dialog');
    var deleteButton = document.querySelector('#btn-delete-site');

    if (!deleteButton) {
        return;
    }

    if (!deleteDialog.showModal) {
        dialogPolyfill.registerDialog(deleteDialog);
    }

    deleteButton.addEventListener('click', function () {
        deleteDialog.showModal();
    });

    deleteDialog.querySelector('.dialog-close').addEventListener('click', function () {
        deleteDialog.close();
    });

    deleteDialog.querySelector('.confirm-delete').addEventListener('click', function () {
        deleteDialog.close();
    });
}

// Returns the most recent 72 hours since the last reading
// function getRecentData(timeSeriesData) {
//     var lastRead = Math.max.apply(Math, timeSeriesData.map(function(value){
//         return new Date(value.DateTime);
//     }));
//
//     var dataTimeOffset = new Date(lastRead - 1000 * 60 * 60 * EXTENT_HOURS);
//     return timeSeriesData.filter(function (value) {
//         return (new Date(value.DateTime)) >= dataTimeOffset;
//     });
// }

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
    // var $lastObservation = card.find(".last-observation");

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

    // $('.plot_box[data-result-id=' + seriesInfo['resultId'] + ' ]').find('.latest-value').text(seriesData[seriesData.length - 1].Value);

    var lastRead = Math.max.apply(Math, seriesData.map(function(value){
        return new Date(value.DateTime);
    }));

    // $lastObservation.text(formatDate(lastRead)); //

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
    $.ajax({
        url: sensorInfo['influxUrl']
    }).done(function(influx_data) {
        var resultSet = influx_data.results.shift();
        if (resultSet.series && resultSet.series.length) {
            var influxSeries = resultSet.series.shift();
            // Get the indexes from the column definitions
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
            //
            // var recentValues = getRecentData(values);
            fillValueTable($('table.data-values[data-result-id=' + sensorInfo['resultId'] + ']'), values);
            drawSparklineOnResize(sensorInfo, values);
            drawSparklinePlot(sensorInfo, values);
        } else {
             console.error('No data values were found for this site');
             console.info(series.getdatainflux);
        }
    }).fail(function(failedData) {
        console.log('data failed to load.');

    })
    // Papa.parse(sensorInfo['csvPath'], {
    //     download: true,
    //     header: true,
    //     worker: true,
    //     comments: "#",
    //     skipEmptyLines: true,
    //     complete: function (result) {
    //         if (result.data) {
    //             var recentValues = getRecentData(result.data);
    //             fillValueTable($('table.data-values[data-result-id=' + sensorInfo['resultId'] + ']'), result.data);
    //             drawSparklineOnResize(sensorInfo, recentValues);
    //             drawSparklinePlot(sensorInfo, recentValues);
    //         }
    //     }
    // });
}

$(document).ready(function () {
    var dialog = document.querySelector('#data-table-dialog');
    if (!dialog.showModal) {
        dialogPolyfill.registerDialog(dialog);
    }

    $("#chkFollow").on("change", function () {
        var statusContainer = $(".follow-status");
        var followForm = $("#follow-site-form");
        var following = !$(this).prop("checked");
        // var tooltip = $(".mdl-tooltip[data-mdl-for='btn-follow']");

        $.ajax({
            url: $('#follow-site-api').val(),
            type: 'post',
            data: {
                csrfmiddlewaretoken: followForm.find('input[name="csrfmiddlewaretoken"]').val(),
                sampling_feature_code: followForm.find('input[name="sampling_feature_code"]').val(),
                action: (following)? 'unfollow': 'follow'
            }}).done(function(data) {
                statusContainer.toggleClass("following");
            // tooltip.text((following)? 'Follow': 'Unfollow');

            var snackbarContainer = document.querySelector('#clipboard-snackbar');

            // var msg = (following)? 'You are now following this site.' : 'This site has been unfollowed.';
            var snackbarMsg = {
                message: (!following)? 'You are now following this site.' : 'This site has been unfollowed.',
                timeout: 3000
            };
            snackbarContainer.MaterialSnackbar.showSnackbar(snackbarMsg);
        });
    });

    $(".table-trigger").click(function () {
        var box = $(this).parents('.plot_box');
        var id = box.data('result-id');
        var tables = $('table.data-values');
        tables.hide();

        tables.filter('[data-result-id="' + id + '"]').show();
        var title = box.data('variable-name') + ' (' + box.data('variable-code') + ')';
        $(dialog).find('.mdl-dialog__title').text(title);
        $(dialog).find('.mdl-dialog__title').attr("title", title);

        dialog.showModal();
    });

    dialog.querySelector('.dialog-close').addEventListener('click', function () {
        dialog.close();
    });

    $('nav .menu-sites-list').addClass('active');


    var sensors = document.querySelectorAll('.device-data .plot_box');
    for (var index = 0; index < sensors.length; index++) {
        var sensorInfo = sensors[index].dataset;
        getTimeSeriesData(sensorInfo);
    }

    bindDeleteDialogEvents();

    // Executes when page loads
    fixViewPort();

    // Executes each time window size changes
    $(window).resize(
        ResponsiveBootstrapToolkit.changed(function () {
            $('.plot_box').height("initial");   // Reset height
            fixViewPort();
        }));
});

function formatDate(date) {
    date = new Date(date);

    var options = {
        year: "numeric", month: "short",
        day: "numeric", hour: "2-digit", minute: "2-digit"
    };

    return date.toLocaleTimeString("en-us", options);
}
