// select correct URL when selecting year
$(".question_replies .select-minister select, .question_replies .select-year form input").change(function() {
  var selectedMinister = $(".select-minister select").val();
  var selectedYear = $(".select-year input:checked").attr("year");

  var params = {};

  if (selectedYear != "all") {
    { params['filter[year]'] = selectedYear }
  };

  if (selectedMinister != "all") {
    { params['filter[minister]'] = selectedMinister }
  };

  window.location.href = "?" + jQuery.param(params);
});