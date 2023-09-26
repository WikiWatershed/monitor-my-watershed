/**
 * Created by HTAO on 6/7/2022.
 */
 $(document).ready(function () {
    $('.datepicker').datepicker({
        format: 'yyyy-mm-dd',
        startDate: '0d'
    });

    // Validation for placement date
    $('#id_placement_date, #id_retrieval_date').change(function () {
        var placement = $('#id_placement_date').val();
        var retrieval = $('#id_retrieval_date').val();
        if (placement && retrieval) {
            var placementDate = new Date(placement);
            var retrievalDate = new Date(retrieval);
            if (placementDate > retrievalDate) {
                $('#id_placement_date')[0].setCustomValidity('Placement date has to be before the retrieval date.');
            }
            else {
                $('#id_placement_date')[0].setCustomValidity('');
                $('#id_retrieval_date')[0].setCustomValidity('');
            }
        }
        else if (!$(this).val()) {
            this.setCustomValidity('Please fill out this field.');
        }
    });

    //not-detected hide float field
    //event handler 
    $('.non-detect').on('change', function(){
        updateNonDetectField(this)
    });
    //initialize
    $('.non-detect').each(function(){updateNonDetectField(this)});

    favorite =[];
    //totalForms = $('#id_2_TOTAL_FORMS');
    let totalForms = document.querySelector("#id_para-TOTAL_FORMS")
    let sensorForm = document.querySelectorAll(".parameter-form")
    let container = document.querySelector("#para-container")
    let addButton = document.querySelector("#para-end")

    let formNum = sensorForm.length-1 // Get the number of the last form on the page with zero-based indexing
    //alert("My selected types are: " + favorite.join(", "));

    $("input[name='0-activity_type']").click(function() {
        favorite =[];
        $.each($("input[name='0-activity_type']:checked"), function(){
            favorite.push($(this).val());
        });
        //alert("My selected types are: " + favorite.join(", "));
    });

    $("form").submit(function() {
        // favorite =[];
        // $.each($("input[name='0-activity_type']:checked"), function(){
        //     favorite.push($(this).val());
        // });
        //alert("My selected types are: " + favorite.join(", "));
    });

    $("#id_sensor-test_method").change(function() {
        //alert("My selected types are: " + $(this).find(":selected").text());

        if($(this).find(":selected").text()!="Meter") { //3rd radiobutton
            $("#id_sensor-calibration_date").attr("disabled", "disabled"); 
            $("#id_sensor-meter").attr("disabled", "disabled"); 
        }
        else {
            $("#id_sensor-calibration_date").removeAttr("disabled"); 
            $("#id_sensor-meter").removeAttr("disabled"); 
        }

    });

    $(".btn-add-parameter").click(function(){
        //alert("Add method clicked!");
        AddSensorParameterForm();
    }); 

    $("#id_conditions-water_odor").change(function() {
        //method to conditionally toggle visibility of the water odor other field
        //if 'other' (value = 441) is selected field should be visible
        //other wise hide the field and clear the entry.  
        toogleWaterOdorOther(this);
    });    

    $(".site-photo-field").change(function() {
        hideSitePhoto(this);
    })

    // tutorial for dynamically adding Forms in Django with Formsets and JavaScript
    // https://www.brennantymrak.com/articles/django-dynamic-formsets-javascript
    
    function AddSensorParameterForm() {
        //e.preventDefault()
    
        const newForm = sensorForm[0].cloneNode(true) //Clone the bird form
        $(newForm).attr('class','row parameter-form');
        let formRegex = RegExp(`parameter-(\\d){1}-`,'g') //Regex to find all instances of the form number

        formNum++ //Increment the form number
        newForm.innerHTML = newForm.innerHTML.replace(formRegex, `para-${formNum}-`) //Update the new form to have the correct form number

        //container.insertBefore(newForm, addButton) //Insert the new form at the end of the list of forms
        //$(newForm).insertBefore( "#btn-add-parameter" );
        $(newForm).val('');
        $('.parameter-card').append($(newForm));
    
        totalForms.setAttribute('value', `${formNum+1}`) //Increment the number of total forms in the management form

    }

    toogleWaterOdorOther("#id_conditions-water_odor");

});

function updateNonDetectField(elem) {
    const id = $(elem).attr('id');
    const checked = $(elem).prop('checked')
    const parent_field_id = id.replace('_nondetect', '');
    $('#' + parent_field_id).parent().attr('hidden', checked);
}

function toogleWaterOdorOther(element) {
    let checkElement = $(element).children().find('[value=441]').parent()
    let otherText = $('#id_conditions-water_odor_other');
    if (checkElement.hasClass('is-checked')) {
        otherText.parent().show();
        
    } else {
        otherText.parent().hide();
        otherText.val('');
    } 
}

function hideSitePhoto(element) {
    let form_field = $(element).parent('.form-field');
    let img = $(form_field).find('img');
    let label = $(form_field).find('label');
    $(img).hide();
    $(form_field).find('p').remove();
    $(label).after($('<p>',{text:"Site photo will be replaced with your upload", style:"font-size:10pt; padding-left:3px;"}));
}
