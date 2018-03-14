var openCount = $(".call-for-comment-stub.open").length;
$(".open-calls-count #count").text(openCount);
if (openCount == 0) {
  $(".no-open-hidden").addClass("hidden");
};