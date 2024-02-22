//jquery ready event
$(function() {
    initSubscriptionDialog();
});

function initSubscriptionDialog() {
    $("#subscription-dialog").dialog({
        dialogClass: "popup",
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

            //when open it will auto focus to first tabable element.
            //this will scroll back to the top
            $(this).scrollTop(0);
        },
        close: function() {
            //disable scrolling (hide overflow) 
            $('body').css({overflow: 'auto'});

        },
        buttons: [
            {
                text: 'Close',
                id: 'popup-close-button',
                click: function() {
                    $(this).dialog('close');
                }
            }
        ]
    })
} 

