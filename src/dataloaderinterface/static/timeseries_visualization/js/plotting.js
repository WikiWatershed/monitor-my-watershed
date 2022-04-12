var _chart
var _axes

function initChart(target_element) {
    _chart = createChart(target_element);
    _axes = [-999, -999, -999, -999, -999, -999];
}


function createChart(renderTo) {
    return new Highcharts.chart(renderTo, {
        chart: {
            plotBorderColor: '#CCC',
            plotBorderWidth: 2,
            type: 'line',
            zoomType: 'xy',
            spacingLeft:20,
            spacingRight:20,
            panning: {
                enabled: true,
                type: 'xy'
            },
            panKey: 'shift',
        },
        credits: {
            enabled: false
        },
        title: {
            text: ''
        },
        subtitle: {
            text: 'Click and drag in the plot area to zoom in, hold "shift" to pan'
        },
        xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: {
                year: '%Y',
                month: "%m/%d/%Y",
                week: "%m/%d/%Y",
                day: "%m/%d/%Y",
                hour: "%m/%d/%Y %k",
                minute: "%m/%d/%Y %k:%M",
                second: "%m/%d/%Y %k:%M:%s"
            },
            labels: {
                style: {
                    fontSize: '14px'
                },
            },
            title: {
                text: 'Monitoring Date (local time of sensor)',
                style: {
                    fontSize: '16px'
                }
            }
        },
        yAxis: [
            {
                type: 'linear',
                title: {
                    text: '',
                    style: {
                        fontSize: '15px'
                    }
                },
                labels: {
                    style: {
                        fontSize: '13px'
                    }
                },
                min: -1,
                showEmpty: false,
            },
            {
                type: 'linear',
                title: {
                    text: '',
                    style: {
                        fontSize: '15px'
                    }
                },
                labels: {
                    style: {
                        fontSize: '13px'
                    },
                },
                min: -1,
                showEmpty: false,
                opposite: true,
            },
            {
                type: 'linear',
                title: {
                    text: '',
                    style: {
                        fontSize: '15px'
                    }
                },
                labels: {
                    style: {
                        fontSize: '13px'
                    }
                },
                showEmpty: false,
                min: -1,
            },
            {
                type: 'linear',
                title: {
                    text: '',
                    style: {
                        fontSize: '15px'
                    }
                },
                labels: {
                    style: {
                        fontSize: '13px'
                    },
                },
                min: -1,
                showEmpty: false,
                opposite: true,
            },
            {
                type: 'linear',
                title: {
                    text: '',
                    style: {
                        fontSize: '15px'
                    }
                },
                labels: {
                    style: {
                        fontSize: '13px'
                    }
                },
                showEmpty: false,
                min: -1,
            },
            {
                type: 'linear',
                title: {
                    text: '',
                    style: {
                        fontSize: '15px'
                    }
                },
                labels: {
                    style: {
                        fontSize: '13px'
                    },
                },
                min: -1,
                showEmpty: false,
                opposite: true,
            }
        ],
        legend: {
            enabled: true,
            layout: 'horizontal',
            align: 'left',
            verticalAlign: 'top',
            backgroundColor: (Highcharts.theme && Highcharts.theme.background2) || 'white',
            borderColor: '#CCC',
            borderWidth: 1,
        },
        tooltip: {
            pointFormat: '{series.name}: <b>' + '{point.y:.1f}' + '</b>',
            dateTimeLabelFormats: {
                year: '%Y',
                month: "%m/%d/%Y",
                week: "%m/%d/%Y",
                day: "%m/%d/%Y",
                hour: "%m/%d/%Y %k",
                minute: "%m/%d/%Y %k:%M",
                second: "%m/%d/%Y %k:%M:%s"
            },
        },
        plotOptions: {
        },
        pane: {
            size: '60%'
        },
        series: []
    });
}

function addSeries(chart, yAxis, axis_title, series_name, x, y) {
    let data = x.map((e,i) => [e,y[i]]);

    let series = chart.addSeries({
        type:'line',
        data:data,
        yAxis: yAxis,
        connectNulls:false,
        name: series_name,
        gapSize: 1000,
    });
    let series_color = series.color;

    let axis = chart.yAxis[yAxis]
    axis.setTitle({'text':axis_title, 'style':{'color':series_color}});
    axis.setTitle({'text':axis_title, 'style':{'color':series_color}});
    axis.update({'ColorString':series_color});
}

function removeSeries(chart, yAxis) {
    let axis = chart.yAxis[yAxis];
    axis.series[0].remove();
    axis.setTitle({text:''})
    axis.setExtremes();
}