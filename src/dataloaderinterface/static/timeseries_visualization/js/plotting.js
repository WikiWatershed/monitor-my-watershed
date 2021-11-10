function initChart(target_element) {
    _chart = createChart(target_element);
    _axes = [-999, -999, -999, -999, -999, -999];
}


function createChart(renderTo) {
     chart = new Highcharts.chart(renderTo, {
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
                day: "%m/%d/%y",
                month: "%b-%y"
            },
            labels: {
                style: {
                    fontSize: '14px'
                }
                /*
                formatter: function () {
                    var dateparts = this.value.split('T')
                    return (dateparts[0])
                }
                */
            },
            title: {
                text: 'Monitoring Date',
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
    axis_count = _chart.yAxis.length;
    axis_buffer = .5 * axis_count % 2;
    
    opposite = false;
    left = -axis_buffer;
    right = 0;
    if (align === "right") {
        opposite = true;
        left = -axis_buffer;
        right = 0;
    }
    axis = _chart.addAxis({
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

function addSeries(yAxis, metadata, x, y) {
    data = x.map((e,i) => [e,y[i]]);

	zlocation_text = ''
	if (metadata.zlocation !== undefined) {
		zlocation_text = `: ${metadata.zlocation} ${metadata.zlocationunits}`
	}

    axis_title = `${metadata.variablecode} - ${metadata.sampledmediumcv}${zlocation_text} (${metadata.unitsabbreviation})`;
    series_name =  `${metadata.variablecode} (${metadata.unitsabbreviation})`;
    series = _chart.addSeries({
        type:'line',
        data:data,
        yAxis: yAxis,
        connectNulls:false,
        name: series_name,
        gapSize: 10,
    });
    series_color = series.color;
    series

    axis = _chart.yAxis[yAxis]
    axis.setTitle({'text':axis_title, 'style':{'color':series_color}});
    axis.setTitle({'text':axis_title, 'style':{'color':series_color}});
    axis.update({'ColorString':series_color});
}

function removeSeries(yAxis) {
    axis = _chart.yAxis[yAxis];
    axis.series[0].remove();
    axis.setTitle({text:''})
}