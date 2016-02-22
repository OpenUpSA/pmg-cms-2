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


  var csrftoken = $('meta[name=csrf-token]').attr('content');

  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    }
  });

  $(".create-alert .btn").on("click", function(e) {

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
      $('.remove-alert').removeClass('hidden').find('.btn').data('id', resp.id);
      ga('send', 'event', 'user', 'add-search-alert');
    });
  });

  $(".remove-alert .btn").on("click", function(e) {

    var id = $(this).data('id') || "";

    $.post(
      '/user/saved-search/' + id + '/delete'
    ).always(function(resp) {
      $('.remove-alert').addClass('hidden').find('.btn').data('id', '');
      $('.create-alert').removeClass('hidden');
      ga('send', 'event', 'user', 'remove-search-alert');
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

$(function() {
  // show more buttons on home page
  $('.show-more').on('click', function() {
    var $btn = $(this);
    var $target = $btn.prev();

    if ($target.hasClass('expanded')) {
      $target.removeClass('expanded');
      $btn.removeClass('show-less');
      $btn.text('Show more');
    } else {
      $target.addClass('expanded');
      $btn.addClass('show-less');
      $btn.text('Show less');
    }
  });
});
