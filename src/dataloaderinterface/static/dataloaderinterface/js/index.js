//jquery ready event
$(function() {
    let width = window.innerWidth * .5;
    let height = window.innerHeight * .6;
    initSubscriptionDialog(width, height);

    window.addEventListener('resize', function(event) {
        resizeSubscriptionDialog();
    }, true);

});

function resizeSubscriptionDialog() {
    let width = window.innerWidth * .5;
    let height = window.innerHeight * .6;
    $("#subscription-dialog").dialog("option", "width", width)
    $("#subscription-dialog").dialog("option", "height", height)
}

function initSubscriptionDialog(width=550, height=350) {
    //check cookies to to see if user has seen in last 24 hours 
    const popupSeen = document.cookie
    .split("; ")
    .find((row) => row.startsWith("popupSeen="))
    ?.split("=")[1];
    if (popupSeen) {return;}
    
    $("#subscription-dialog").dialog({
        dialogClass: "popup",
        autoOpen: true,
        minWidth: 550,
        minHeight: 350,
        maxHeight: 650,
        maxWidth: 950,
        width: width,
        height: height,
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
            document.cookie = "popupSeen=true; max-age=86400*30;"

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

