// Hua Tao 2019/10/14
// Add a sensitive group plot

$(document).ready(function(){

    var margin = {top: 40, right: 20, bottom: 60, left: 80},
    width = $(".svg-container2").width() - margin.left - margin.right,
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
            return d.name + "<br><br><strong>% of Total Individuals:</strong> <span style='color:red'>" + (d.count * 100).toFixed(2) + "%</span>";
        });

    var group = [{color: d3.rgb("#00A0D3")}, // turquoise
                 {color:d3.rgb("#7B439A")}, // dark purple
                 {color:d3.rgb("#EE7E22")}]; //orange

    var total =0;

    $('table.macroinv').each(function(i) {
        group[i].name = $(this).attr("data-group"); 
        var groupTotal =0;
        $(this).find('.taxon').each(function() {
            groupTotal = groupTotal + parseFloat($(this).find("[data-count]").text().trim());
        })
        group[i].count = groupTotal;
        total = total + groupTotal;
    });

    var legendContainer = $("#legend-container2 table");
    
    for (var i=0; i< group.length; i++) {
        group[i].count = group[i].count / total;
        var f = isNaN(group[i].count) ? "0" : (group[i].count * 100).toFixed(2);
        legendContainer.append(
            '<tr>' +
            '<td><i style="color: ' + group[i].color + '" class="fa fa-square mdl-list__item-icon" aria-hidden="true"></i></td>' +
            '<td class="mdl-data-table__cell--non-numeric">' +
            group[i].name +
            '</td>' +
            '<td>' + f + '%</td>' +
            '</tr>'
        );
    }

    var svg2 = d3.select(".svg-container2").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    svg2.call(tip);


    // Plot the data
    x.domain(group.map(function (d) {
        return d.name;
    }));

    // Comment out to use 0 to 100% domain
    y.domain([0, d3.max(group, function (d) {
        return d.count;
    })]);

    svg2.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .append("text")
        .attr("class", "label")
        .style("text-anchor", "middle")
        .attr("x", width / 2)
        .attr("y", margin.bottom / 2)
        .text("Sensitivity Group");

    svg2.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("x", -height / 2)
        .attr("y", -(margin.left - 10))
        .attr("dy", ".71em")
        .style("text-anchor", "middle")
        .text("Count");

    svg2.selectAll(".bar")
        .data(group)
        .enter().append("rect")
        .attr("class", "bar")
        .attr("x", function (d) {
            return x(d.name);
        })
        .attr("width", x.rangeBand())
        .attr("y", function (d) {
            return y(d.count);
        })
        .attr("fill", function (d, i) {
            return group[i].color;
        })
        .attr("height", function (d) {
            return height - y(d.count);
        })
        .on('mouseover', tip.show)
        .on('mouseout', tip.hide);

})