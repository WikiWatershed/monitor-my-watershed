//jquery ready event
$(function() {
    initSubscriptionDialog();
});

function initSubscriptionDialog() {
    $("#subscription-dialog").dialog({
        autoOpen: true,
        width: 950,
        height: 650,
        modal: true,
        resizable: true,
        title:'Upcoming Changes',
        open: function() {
            //hide the x on the dialog title
            $(this).parent().find(".ui-dialog-titlebar-close").hide();

            //disable scrolling (hide overflow) 
            $('body').css({overflow: 'hidden'});
        },
        close: function() {
            //disable scrolling (hide overflow) 
            $('body').css({overflow: 'auto'});

        },
        buttons: [
            {
                text: 'Close',
                click: function() {
                    $(this).dialog('close');
                }
            }
        ]
    })
} 