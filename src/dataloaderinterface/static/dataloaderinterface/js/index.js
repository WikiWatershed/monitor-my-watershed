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
        title:'Upcoming Changes'
    })
} 