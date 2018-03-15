var openProvincialCount = $("section.calls-for-comment .open-call").length;
$("section.calls-for-comment #open-calls").text(openProvincialCount);
if (openProvincialCount > 0) {
  $(".open-calls-count").removeClass("hidden");
  $(".no-open-calls").addClass("hidden");
};