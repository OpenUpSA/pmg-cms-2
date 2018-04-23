var url = window.location.href;
var hansardFilter = "house_id";

if(url.indexOf(hansardFilter) != -1 )
  var lastChar = url.slice(-1);
  if($.isNumeric(lastChar));
    var lastChar = parseInt(lastChar, 10);
    $(".hansards .select-house option[value=" + lastChar + "]").prop("selected",true);

if($(".hansards ul.hansard-list > li").length == 0)
  $(".hansards ul.hansard-list").append("<li>No hansards for this house</li>");