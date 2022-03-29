function initChart(target_element) {
    _chart = createChart(target_element);
    _axes = [-999, -999, -999, -999, -999, -999];
}


function createChart(renderTo) {
    let chart = new Highcharts.chart(renderTo, {
        chart: {
            plotBorderColor: '#CCC',
            plotBorderWidth: 2,
            type: 'line',
            zoomType: 'x',
            height:700,
            spacingLeft:20,
            spacingRight:20,
        },
        credits: {
            enabled: false
        },
        title: {
            text: ''
        },
        subtitle: {
            text: 'Click and drag in the plot area to zoom in'
        },
        xAxis: {
            type: 'datetime',
            //tickInterval: 30,
            //tickWidth: 1,
            dateTimeLabelFormats: {
                day: "%m/%d/%Y",
                month: "%m/%d/%Y"
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
            pointFormat: '{series.name}: <b>' + '{point.y:.1f}' + '</b>'
        },
        plotOptions: {
        },
        pane: {
            size: '60%'
        },
        series: []
    });
    return chart;
}

function addYAxis(align="left") {
    let axis_count = _chart.yAxis.length;
    let axis_buffer = .5 * axis_count % 2;
    
    let opposite = false;
    let left = -axis_buffer;
    let right = 0;
    if (align === "right") {
        opposite = true;
        left = -axis_buffer;
        right = 0;
    }
    let axis = _chart.addAxis({
        type: 'linear',
        title: {
            text: '',
            style: {
                fontSize: '15px'
            }
        },
        labels: {
            align: align,
            style: {
                fontSize: '13px'
            }
        },
        min: -1,
        opposite: opposite,
    });
    _chart.redraw();
}

function addSeries(yAxis, axis_title, series_name, x, y) {
    let data = x.map((e,i) => [e,y[i]]);

    let series = _chart.addSeries({
        type:'line',
        data:data,
        yAxis: yAxis,
        connectNulls:false,
        name: series_name,
        gapSize: 1000,
    });
    let series_color = series.color;

    let axis = _chart.yAxis[yAxis]
    axis.setTitle({'text':axis_title, 'style':{'color':series_color}});
    axis.setTitle({'text':axis_title, 'style':{'color':series_color}});
    axis.update({'ColorString':series_color});
    let extremes = axis.getExtremes();
    axis.setExtremes(extremes.dataMin,extremes.dataMax);
}

function removeSeries(yAxis) {
    let axis = _chart.yAxis[yAxis];
    axis.series[0].remove();
    axis.setTitle({text:''})
    axis.setExtremes();
}