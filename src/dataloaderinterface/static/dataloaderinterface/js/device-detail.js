const EXTENT_HOURS = 72;
const DATA_TIME_OFFSET = new Date(new Date() - 1000 * 60 * 60 * EXTENT_HOURS);

function initMap() {
    var defaultZoomLevel = 18;
    var latitude = parseFloat($('#site-latitude').val());
    var longitude = parseFloat($('#site-longitude').val());
    var sitePosition = {lat: latitude, lng: longitude};

    var map = new google.maps.Map(document.getElementById('map'), {
        center: sitePosition,
        scrollwheel: false,
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

function getRecentData(timeSeriesData) {
    return timeSeriesData.filter(function (value) {
        return (new Date(value.DateTime)) >= DATA_TIME_OFFSET;
    });
}

function fillValueTable(table, data) {
    var rows = data.map(function (dataValue) {
        return $("<tr><td class='mdl-data-table__cell--non-numeric'>" + dataValue.DateTime + "</td><td class='mdl-data-table__cell--non-numeric'>" + dataValue.TimeOffset + "</td><td>" + dataValue.Value + "</td></tr>");
    });
    table.append(rows);
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
    var plotBox = $('div.plot_box[data-result-id="' + seriesInfo['resultId'] + '"] div.graph-container');
    plotBox.empty();

    var margin = {top: 5, right: 1, bottom: 5, left: 1};
    var width = plotBox.width() - margin.left - margin.right;
    var height = plotBox.height() - margin.top - margin.bottom;

    if (seriesData.length === 0) {
        // Append message when there is no data
        d3.select(plotBox.get(0)).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("text")
                .text("No data in the last 72 hours.")
                .attr("font-size", "12px")
                .attr("fill", "#AAA")
                .attr("text-anchor", "left")
                .attr("transform", "translate(" + (margin.left + 10) + "," + (margin.top + 20) + ")");
        return;
    }

    $('.plot_box[data-result-id=' + seriesInfo['resultId'] + ' ]').find('.latest-value').text(seriesData[seriesData.length - 1].Value);

    var xAxis = d3.scaleTime().range([0, width]);
    var yAxis = d3.scaleLinear().range([height, 0]);

    xAxis.domain([DATA_TIME_OFFSET, new Date()]);
    yAxis.domain(d3.extent(seriesData, function(d) {
        return d.Value;
    }));

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
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    svg.append("path")
        .data([seriesData])
        .attr("class", "line").attr("d", line)
        .attr("stroke", "steelblue");
}

function getTimeSeriesData(sensorInfo) {
    Papa.parse(sensorInfo['csvPath'], {
        download: true,
        header: true,
        comments: "#",
        skipEmptyLines: true,
        complete: function(result) {
            var recentValues = getRecentData(result.data);
            fillValueTable($('table.data-values[data-result-id=' + sensorInfo['resultId'] + ']'), result.data);
            drawSparklineOnResize(sensorInfo, recentValues);
            drawSparklinePlot(sensorInfo, recentValues);
        }
    });
}

$(document).ready(function () {
    var dialog = document.querySelector('#data-table-dialog');
    if (!dialog.showModal) {
        dialogPolyfill.registerDialog(dialog);
    }

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
        })
    );
});
