/**
 * Created by Mauriel on 5/16/2018.
 */
var c20 = d3.scale.category20();

var margin = {top: 80, right: 20, bottom: 60, left: 80},
    width = $(".svg-container").width() - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom;

var formatPercent = d3.format(".0%");

var x = d3.scale.ordinal()
    .rangeRoundBands([0, width], .1);

var y = d3.scale.linear()
    .domain([0, 1])
    .range([height, 0]);

var xAxis = d3.svg.axis()
    .scale(x)
    .tickValues([])
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left")
    .tickFormat(formatPercent);

var tip = d3.tip()
    .attr('class', 'd3-tip')
    .offset([-10, 0])
    .html(function (d) {
        return d.taxon + "<br><br><strong>% of Total Individuals:</strong> <span style='color:red'>" + (d.frequency * 100).toFixed(2) + "%</span>";
    });

var svg = d3.select(".svg-container").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

svg.call(tip);

// Get the data
var data = [];
var total = 0;
$(".taxon").each(function () {
    var name = $(this).find("[data-name]").text().trim();
    var count = parseFloat($(this).find("[data-count]").text().trim());
    data.push({taxon: name, frequency: count});
    total += count;
});

var legendContainert0 = $("#legend-container-t0 table");
var legendContainert1 = $("#legend-container-t1 table");
var legendContainert2 = $("#legend-container-t2 table");

// Compute percentages
for (var i = 0; i < data.length; i++) {
    data[i].frequency = data[i].frequency / total;
    var f = isNaN(data[i].frequency) ? "0" : (data[i].frequency * 100).toFixed(2);
    var id = i % 3;
    var $container;

    if (id===0) {
        $container = legendContainert0;
    } else if (id===1) {
        $container = legendContainert1;
    } else {
        $container = legendContainert2;
    }
    // Populate legend container
    $container.append(
        '<tr>' +
        '<td><i style="color: ' + c20(i) + '" class="fa fa-square mdl-list__item-icon" aria-hidden="true"></i></td>' +
        '<td class="mdl-data-table__cell--non-numeric">' +
        data[i].taxon +
        '</td>' +
        '<td>' + f + '%</td>' +
        '</tr>'
    );
}

// Plot the data
x.domain(data.map(function (d) {
    return d.taxon;
}));

// Comment out to use 0 to 100% domain
y.domain([0, d3.max(data, function (d) {
    return d.frequency;
})]);

// Define responsive behavior
function resize() {
    width = $(".svg-container").width() - margin.left - margin.right;

    // Update the range of the scale with new width/height
    x.rangeRoundBands([0, width], .1);

    // Update the axis and text with the new scale
    svg.select(".x.axis")
        .call(xAxis)
        .attr("transform", "translate(0," + height + ")")
        .select(".label")
        .attr("x", width / 2)
        .attr("y", margin.bottom / 1.5);

    svg.select(".y.axis")
        .call(yAxis);

    // Force D3 to recalculate and update the line
    svg.selectAll(".bar")
        .attr("width", x.rangeBand())
        .attr("y", function (d) {
            return y(d.frequency);
        })
        .attr("x", function (d) {
            return x(d.taxon);
        })
        .attr("height", function (d) {
            return height - y(d.frequency);
        })
        .on('mouseover', tip.show)
        .on('mouseout', tip.hide);
}

// Call the resize function whenever a resize event occurs
d3.select(window).on('resize', resize);

function type(d) {
    d.frequency = +d.frequency;
    return d;
}

// Example at: https://bl.ocks.org/mbostock/3885705
function change() {
    // Copy-on-write since tweens are evaluated after a delay.
    var x0;

    if (this.checked) {
        x0 = x.domain(data.slice().sort( function(a, b) { return b.frequency - a.frequency; })
            .map(function(d) { return d.taxon; }))
            .copy();
    }
    else {
        x0 = x.domain(data.slice().map(function(d) { return d.taxon; })).copy();
    }

    svg.selectAll(".bar")
        .sort(function (a, b) {
            return x0(a.taxon) - x0(b.taxon);
        });

    var transition = svg.transition().duration(750),
        delay = function (d, i) {
            return i * 50;
        };

    transition.selectAll(".bar")
        .delay(delay)
        .attr("x", function (d) {
            return x0(d.taxon);
        });

    transition.select(".x.axis")
        .call(xAxis)
        .selectAll("g")
        .delay(delay);
    
}

$(document).ready(function () {
    d3.select("input").on("change", change);
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .append("text")
        .attr("class", "label")
        .style("text-anchor", "middle")
        .attr("x", width / 2)
        .attr("y", margin.bottom / 2)
        .text("Taxonomic Group");

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("x", -height / 2)
        .attr("y", -(margin.left - 10))
        .attr("dy", ".71em")
        .style("text-anchor", "middle")
        .text("% of Total Individuals");

    svg.append("text")
        .attr("x", (width / 2))             
        .attr("y", 0 - (margin.top / 2))
        .attr("text-anchor", "middle")  
        .style("font-size", "16px") 
        .style("text-decoration", "underline")  
        .text("Relative Abundance of Macroinvertebrate Taxa");

    svg.selectAll(".bar")
        .data(data)
        .enter().append("rect")
        .attr("class", "bar")
        .attr("x", function (d) {
            return x(d.taxon);
        })
        .attr("width", x.rangeBand())
        .attr("y", function (d) {
            return y(d.frequency);
        })
        .attr("fill", function (d, i) {
            return c20(i);
        })
        .attr("height", function (d) {
            return height - y(d.frequency);
        })
        .on('mouseover', tip.show)
        .on('mouseout', tip.hide);

    $("#chkSortBars").change(change);
});
