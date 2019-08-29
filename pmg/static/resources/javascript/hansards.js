// select correct URL when selecting house or year
$(".hansards .select-house select, .hansards .select-year form input").change(function() {
  var selectedHouse = $(".select-house select").val();
  var selectedYear = $(".select-year input:checked").attr("year");

  var params = {};

  if (selectedYear != "all") {
    { params['filter[year]'] = selectedYear }
  };

  if (selectedHouse != "all") {
    { params['filter[house_id]'] = selectedHouse }
  };

  window.location.href = "?" + jQuery.param(params);
});