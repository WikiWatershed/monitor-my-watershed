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

    $("#id_had_storm").change(function () {
        var val = parseInt($(this).val());
        var collapse = $("#storm-additional");
        var items = collapse.find("input");
        if (val == 2) {
            items.each(function () {
                if ($(this).attr("data-name")) {
                    $(this).attr("name", $(this).attr("data-name"));
                    $(this).removeAttr("data-name");
                }
                $(this).prop('required', true);
            });
            $("#storm-additional").collapse('show');
        }
        else {
            items.each(function () {
                if ($(this).attr("name")) {
                    $(this).attr("data-name", $(this).attr("name"));
                    $(this).removeAttr("name");
                }
                $(this).prop('required', false);
            });
            $("#storm-additional").collapse('hide');
        }
    });

    // Trigger on page load to set properties
    $("#id_had_storm").trigger("change");
    $('#d_placement_date, #id_retrieval_date').trigger("change");

    $(".bug-count").change(function() {
        var items = $(this).closest(".mdl-card").find(".bug-count");
        var count = 0;
        var total = $(this).closest(".mdl-card").find(".bug-total-count");

        items.each(function () {
            var val = $(this).val();
            if (val) {
                count += parseInt(val);
            }
        });

        total.val(Math.max(total.val(), count));
    });

    $(".bug-total-count").change(function() {
        var items = $(this).closest(".mdl-card").find(".bug-count");
        var count = 0;
        var total = $(this).closest(".mdl-card").find(".bug-total-count");

        items.each(function () {
            var val = $(this).val();
            if (val) {
                count += parseInt(val);
            }
        });

        if (count > total.val()) {
            $(items).val("");
        }
    });
});