var openCount = $(".call-for-comment-stub.open").length;
$(".open-calls-count #count").text(openCount);
if (openCount > 0) {
  $(".open-calls-count").removeClass("hidden");
};

var lastOpen = $(".call-for-comment-stub.open").last();
var lastOpenCol = $(lastOpen).parent().parent();
$(lastOpenCol).after("<div class='row'><div class='col-xs-12 col-lg-6'><div class='col-xs-12'><h3>It is not possible to share your input on closed calls for comments. However, you can still access the relevant contact information to send queries about a call for comment.</h3></div></div></div>");