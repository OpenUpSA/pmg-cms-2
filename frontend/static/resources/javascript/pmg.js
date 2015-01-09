$(function() {
	$(".collapse-link").on("click", function(e) {
		e.preventDefault();
		$(this).next(".collapse").toggle(400, function(test) {
			if ($(this).css("display") == "block") {
				$(this).prev(".collapse-link").find(".fa").removeClass("fa-caret-right").addClass("fa-caret-down");
			} else {
				$(this).prev(".collapse-link").find(".fa").removeClass("fa-caret-down").addClass("fa-caret-right");
			}
		});
	});

	$(".chosen").chosen({width: "100%"});
})
