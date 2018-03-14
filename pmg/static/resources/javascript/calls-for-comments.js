var openCount = $(".call-for-comment-stub.open").length;
$(".open-calls-count #count").text(openCount);
if (openCount > 0) {
  $(".open-calls-count").removeClass("hidden");
};