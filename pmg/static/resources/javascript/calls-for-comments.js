var openCount = $(".call-for-comment-stub.open").length;
$(".open-calls-count #count").text(openCount);

var lastOpen = $(".call-for-comment-stub.open").last();
var lastOpenCol = $(lastOpen).parent().parent();
$(lastOpenCol).after("<div class='col-xs-12 col-sm-6 col-lg-4'>");