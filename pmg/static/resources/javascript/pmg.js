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

	$(".create-alert").on("click", function(e) {

		var q = $(this).data('q'),
			  committee_id = $(this).data('committee') || "",
				content_type = $(this).data('type');

		$.post(
			'/user/saved-search/',
			{
				q: q,
				committee_id: committee_id,
				content_type: content_type
			}
		).done(function(resp) {
			$('.create-alert').addClass('hidden');
			$('.remove-alert').removeClass('hidden').data('id', resp.id);
		});
	});

	$(".remove-alert").on("click", function(e) {

		var id = $(this).data('id') || "";

		$.post(
			'/user/saved-search/' + id
		).always(function(resp) {
			$('.remove-alert').addClass('hidden').data('id', '');
			$('.create-alert').removeClass('hidden');
		});
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
