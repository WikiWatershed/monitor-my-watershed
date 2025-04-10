const EXTENT_HOURS = 72;
const GAP_HOURS = 6;
const STALE_DATA_CUTOFF = new Date(new Date() - 1000 * 60 * 60 * EXTENT_HOURS);

const LOCAL_UTC_OFFSET = new Date().getTimezoneOffset() / 60; //in hours

function initMap() {
  var defaultZoomLevel = 18;
  var latitude = parseFloat($("#site-latitude").val());
  var longitude = parseFloat($("#site-longitude").val());
  var sitePosition = { lat: latitude, lng: longitude };

  var map = new google.maps.Map(document.getElementById("map"), {
    center: sitePosition,
    gestureHandling: "greedy",
    zoom: defaultZoomLevel,
    mapTypeId: google.maps.MapTypeId.HYBRID,
  });

  map.setOptions({ minZoom: 3, maxZoom: 18 });

  var marker = new google.maps.Marker({
    position: sitePosition,
    map: map,
  });
}

function format_date(date) {
  year = String(date.getFullYear()).padStart(4, "0");
  month = String(date.getMonth() + 1).padStart(2, "0");
  day = String(date.getDate()).padStart(2, "0");
  hour = String(date.getHours()).padStart(2, "0");
  minute = String(date.getMinutes()).padStart(2, "0");
  second = String(date.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

function fillValueTable(table, data) {
  var rows = data.map(function (dataValue) {
    //looks to be 1 hour offset between python datetime integer and JS
    date = new Date(
      dataValue.valuedatetime +
        (dataValue.valuedatetimeutcoffset + LOCAL_UTC_OFFSET) * 3600000
    );
    var row_string =
      "<tr><td class='mdl-data-table__cell--non-numeric'>" +
      format_date(date) +
      "</td><td class='mdl-data-table__cell--non-numeric'>" +
      dataValue.valuedatetimeutcoffset +
      "</td><td>" +
      dataValue.datavalue +
      "</td></tr>";
    return row_string;
  });
  table.append($(rows.join("")));
}

function drawSparklineOnResize(seriesInfo, seriesData) {
  var resizeTimer;
  window.addEventListener("resize", function (event) {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      drawSparklinePlot(seriesInfo, seriesData);
    }, 500);
  });
}

function drawSparklinePlot(seriesInfo, seriesData) {
  var card = $('div.plot_box[data-result-id="' + seriesInfo["resultId"] + '"]');
  var plotBox = card.find(".graph-container");

  plotBox.empty();

  var margin = { top: 5, right: 1, bottom: 5, left: 1 };
  var width = plotBox.width() - margin.left - margin.right;
  var height = plotBox.height() - margin.top - margin.bottom;

  if (seriesData.length === 0) {
    card.find(".table-trigger").toggleClass("disabled", true);
    card.find(".download-trigger").toggleClass("disabled", true);
    card.find(".tsa-trigger").toggleClass("disabled", true);

    // Append message when there is no data
    d3.select(plotBox.get(0))
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("text")
      .text("No data exist for this variable.")
      .attr("font-size", "12px")
      .attr("fill", "#AAA")
      .attr("text-anchor", "left")
      .attr(
        "transform",
        "translate(" + (margin.left + 10) + "," + (margin.top + 20) + ")"
      );
    return;
  }

  var lastRead = Math.max.apply(
    Math,
    seriesData.map(function (value) {
      return new Date(value.valuedatetime);
    })
  );

  var dataTimeOffset = Math.min.apply(
    Math,
    seriesData.map(function (value) {
      return new Date(value.valuedatetime);
    })
  );

  var xAxis = d3.scaleTime().range([0, width]);
  var yAxis = d3.scaleLinear().range([height, 0]);

  var yDomain = d3.extent(seriesData, function (d) {
    return parseFloat(d.datavalue);
  });
  var yPadding = (yDomain[1] - yDomain[0]) / 20; // 5% padding
  yDomain[0] -= yPadding;
  yDomain[1] += yPadding;

  xAxis.domain([dataTimeOffset, lastRead]);
  yAxis.domain(yDomain);

  var line = d3
    .line()
    .x(function (d) {
      var date = new Date(d.valuedatetime);
      return xAxis(date);
    })
    .y(function (d) {
      return yAxis(d.datavalue);
    });

  var svg = d3
    .select(plotBox.get(0))
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("class", function () {
      if (lastRead <= STALE_DATA_CUTOFF) {
        return "stale";
      }

      return "not-stale";
    })
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  // Rendering the paths
  var gapOffset; // The minimum date required before being considered a gap.
  var previousDate;
  var start = 0; // Latest start detected after a gap. Initially set to the start of the list.
  var paths = [];

  for (var i = 0; i < seriesData.length; i++) {
    var currentDate = new Date(seriesData[i].valuedatetime);

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
  } else {
    paths.push(seriesData); // No gaps were detected. Just plot the entire original data.
  }

  // Plot all paths separately to display gaps between them.
  for (var i = 0; i < paths.length; i++) {
    if (paths[i].length == 1) {
      svg
        .append("circle")
        .attr("r", 2)
        .style("fill", "steelblue")
        .attr(
          "transform",
          "translate(" +
            xAxis(new Date(paths[i][0].valuedatetime)) +
            ", " +
            yAxis(paths[i][0].datavalue) +
            ")"
        );
    } else {
      svg
        .append("path")
        .data([paths[i]])
        .attr("class", "line")
        .attr("d", line)
        .attr("stroke", "steelblue");
    }
  }
}

function getTimeSeriesData(sensorInfo) {
  request_data = {
    method: "get_result_timeseries",
    resultid: sensorInfo["resultId"],
    interval: 3,
    orient: "records",
  };
  $.ajax({
    url: "../../dataloader/ajax/",
    data: { request_data: JSON.stringify(request_data) },
    method: "POST",
    success: function (data) {
      response_data = JSON.parse(data);
      $table = $(
        "table.data-values[data-result-id=" + sensorInfo["resultId"] + "]"
      );
      fillValueTable($table, response_data);
      drawSparklineOnResize(sensorInfo, response_data);
      drawSparklinePlot(sensorInfo, response_data);
      /*
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
            */
    },
    fail: function () {
      drawSparklinePlot(sensorInfo, []); // Will just render the empty message
      console.log("data failed to load.");
    },
  });
}

function openCSVDownloadDialog(resultIds, maxDate) {
  $("#csv-export-dialog").dialog({
    modal: true, // Make it a modal dialog
    width: 400, // Set the dialog width
    closeOnEscape: false,
    dialogClass: 'no-close no-title-close', // Added no-title-close class
    title: 'Select dates for download',
    buttons: {
      //"Download All": function () {
      //  DownloadCSV(resultIds, undefined, undefined);
      //},
      Close: function () {
        $(this).dialog("close");
      },
      Download: function () {
        var maxDatetime = $(this).find("#csv-max-datetime").val();
        var minDatetime = $(this).find("#csv-min-datetime").val();
        downloadCSV(resultIds, maxDatetime, minDatetime);
      },
    },
    open: function () {
      const date = maxDate ? new Date(Date.parse(maxDate)) : new Date();
      //add one day to make sure we get all the measurement for the day latest day
      if (maxDate) {date.setDate(date.getDate() + 1);}
      const minDate = new Date(date);
      minDate.setMonth(minDate.getMonth() - 1);
      
      $(this)
        .find("#csv-min-datetime")
        .val(minDate.toISOString().split('T')[0]);
      $(this).find("#csv-max-datetime").val(date.toISOString().split('T')[0]);
    },
  });
}

function downloadCSV(resultIds, maxDatetime, minDatetime) {
  const request_data = {
    result_ids: resultIds,
  };

  //dates are optional filter fields and should be situtationally applied
  if (maxDatetime && maxDatetime !== "") {request_data["max_datetime"] = maxDatetime;}
  if (minDatetime && minDatetime !== "") {request_data["min_datetime"] = minDatetime;}

  var link = document.createElement("a");
  link.href = "/api/csv-values/?" + new URLSearchParams(request_data).toString();
  link.setAttribute("download", "data.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  $("#csv-export-dialog").dialog("close");
}

$(document).ready(function () {

  var dialog = $("#data-table-dialog");
  $("#chkFollow").on("change", function () {
    var statusContainer = $(".follow-status");
    var followForm = $("#follow-site-form");
    var following = !$(this).prop("checked");

    $.ajax({
      url: $("#follow-site-api").val(),
      type: "post",
      data: {
        csrfmiddlewaretoken: followForm
          .find('input[name="csrfmiddlewaretoken"]')
          .val(),
        sampling_feature_code: followForm
          .find('input[name="sampling_feature_code"]')
          .val(),
        action: following ? "unfollow" : "follow",
      },
    }).done(function () {
      statusContainer.toggleClass("following");
      var message = !following
        ? "You are now following this site."
        : "This site has been unfollowed.";
      snackbarMsg(message);
    });
  });

  $(".table-trigger").click(function () {
    var box = $(this).parents(".plot_box");
    var id = box.data("result-id");
    var tables = $("table.data-values");
    tables.hide();

    tables.filter('[data-result-id="' + id + '"]').show();
    var title =
      box.data("variable-name") + " (" + box.data("variable-code") + ")";
    dialog.find(".mdl-dialog__title").text(title);
    dialog.find(".mdl-dialog__title").attr("title", title);

    dialog.modal("show");
  });

  $("nav .menu-sites-list").addClass("active");

  var sensors = document.querySelectorAll(".sparkline-plots .plot_box");
  for (var index = 0; index < sensors.length; index++) {
    var sensorInfo = sensors[index].dataset;
    getTimeSeriesData(sensorInfo);
  }

  $(".csv-download").click(function () {
    const resultIds = $(this).attr("result-ids");
    const maxDate = $(this).attr("recent-date");

    openCSVDownloadDialog(resultIds, maxDate);
    //downloadCSV(resultid, maxDatetime, minDatetime);
  });
});
