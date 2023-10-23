//jquery ready event
$(function() {
    initSubscriptionDialog();

    $('#subscription-dialog').on('scroll', function() {
        if( this.scrollTop >= (this.scrollHeight - this.offsetHeight) *.9)
        {
            $('#popup-close-button').prop('disabled',false);
        }
    });
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

            //disable close button until you scroll to the bottom
            $('#popup-close-button').prop('disabled',true);
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

