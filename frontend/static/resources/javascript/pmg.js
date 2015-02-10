$(function() {
	$(".collapse-link").on("click", function(e) {
		e.preventDefault();
		$(this).next(".collapse").toggle(300, function(test) {
			if ($(this).css("display") == "block") {
				$(this).addClass("in");
				$(this).prev(".collapse-link").find(".fa").removeClass("fa-caret-right").addClass("fa-caret-down");
			} else {
				$(this).removeClass("in");
				$(this).prev(".collapse-link").find(".fa").removeClass("fa-caret-down").addClass("fa-caret-right");
			}
		});
	});

	$(".chosen").chosen({width: "100%"});
});

// handle 404 page
$(function() {
	if ($('#page-404').length > 0) {
		ga('send', 'event', '404', document.location.pathname, document.referrer);
	}
});
