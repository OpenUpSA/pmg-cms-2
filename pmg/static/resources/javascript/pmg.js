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


	var csrftoken = $('meta[name=csrf-token]').attr('content')

	$.ajaxSetup({
	    beforeSend: function(xhr, settings) {
	        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
	            xhr.setRequestHeader("X-CSRFToken", csrftoken)
	        }
	    }
	})

	function getURLParameter(name) {
   if(name=(new RegExp('[?&]'+encodeURIComponent(name)+'=([^&]*)')).exec(location.search))
      return decodeURIComponent(name[1]);
	}

	$(".create-alert").on("click", function(e) {
		$.post(
			'/user/saved-search/',
			{
				q: getURLParameter('q'),
				committee_id: getURLParameter('filter[committee]'),
				content_type: getURLParameter('filter[type]')
			}
		);
	});

	$(".chosen").chosen({width: "100%"});
	$('[title]').tooltip();
});

// handle 404 page
$(function() {
	if ($('#page-404').length > 0) {
		ga('send', 'event', '404', document.location.pathname, document.referrer);
	}
});
