class TimeSeries {

	constructor(resultId, startDate, endDate) {
		this.resultId = resultId;
		this.startDate = startDate;
		this.endDate = endDate;
        this.dates = [];
        this.values = [];
	}

    static async build(resultId, startDate, endDate) {
        let instance = new TimeSeries(resultId, startDate, endDate);
        await instance.#getData(startDate, endDate);
        return instance;
    }

	async #getData(startDate, endDate) {
		let requestData = {
            'method': 'get_result_timeseries',
            'resultid': this.resultId,
            'start_date' : startDate,
            'end_date': endDate
        }
        //with bounds of $ajax 'this' references the ajax object
        //store reference to class instance so that we can still reference
        //within the scope of the ajax call
        let instance = this; 
        await $.ajax({
            url: '/dataloader/ajax/',
            data: {request_data: JSON.stringify(requestData)},
            method: 'POST',
            success: function(response) {
                if (typeof (response) !== 'undefined') {
                    instance.startDate = startDate;
                    let response_json = JSON.parse(response);
                    let additional_dates = Object.values(response_json.valuedatetime);
                    let additional_values = Object.values(response_json.datavalue);
                    instance.dates = additional_dates.concat(instance.dates);
		            instance.values = additional_values.concat(instance.values);
                }
            },
            fail: function(response) {
                if (typeof (response) !== 'undefined') {
                    return response	;
                }
    	    }
        });
        return;
    }



    getAdditionData(startDate) {
        if (startDate <= this.startDate) {return;}
        let requiredStart = startDate;
        let requiredEnd = this.startDate;
        this.#getData(requiredStart, requiredEnd);
    }

}