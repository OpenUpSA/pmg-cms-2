// select correct URL when selecting house or year
$(".select-house select, .select-year form input").change(function() {
  var filterHouse = "";
  var filterYear = "";
  var selectedHouse = $(".select-house select").val();
  var selectedYear = $(".select-year input:checked").attr("year");
  var ampersand = ""
  if(selectedHouse) {
    var filterHouse = "filter[house_id]=";
        ampersand = "&";
  }
  if(selectedYear != "all")
    var filterYear = "filter[year]=";
  window.location.href = "/hansards/?" + filterHouse + selectedHouse + ampersand + filterYear + selectedYear;
});