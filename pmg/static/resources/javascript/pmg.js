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
      if ($target.hasClass('feature-cards')) {
      	ga('send', 'event', 'featured', 'show-more');
      } else {
      	switch ($target.parent().attr('class').replace('subsection', '').trim()) {
      		case 'committee-meetings':
      			ga('send', 'event', 'committee-meetings', 'show-more');
      			break;
      		case 'bills':
      			ga('send', 'event', 'bills', 'show-more');
      			break;
      		case 'questions':
      			ga('send', 'event', 'questions', 'show-more');
      			break;
      	}
      }
    }
  });
});

// user creation form
$('form[name=register_user_form]').on('submit', function() {
  $(this).find('input[type=submit]').prop('disabled', true);
});

$(function() {
  var initialised = false;
  var initialise = function() {
    SC.initialize({
      client_id: $('#soundcloud-container').data('soundcloud-id')
    });
  };
  var $audioLinks = $('a.audio');

  $audioLinks.each(function(i, a) {
    a = $(a);
    if (a.data('soundcloud-uri')) {
      var uri = a.data('soundcloud-uri');
      console.log('registering click');
      a.on('click', function(e) {
        console.log('clicked');
        if (!initialised) initialise();
        SC.oEmbed(uri, {
          element: document.getElementById('soundcloud-container'),
          maxheight: 166,
          show_comments: false,
          auto_play: false,
        });
        return false;
      });
    }

    // Convert first link to soundcloud embed
    var firstUri = $audioLinks.first().data('soundcloud-uri');

    if(firstUri) {
      SC.oEmbed(firstUri, {
        element: document.getElementById('soundcloud-container'),
        maxheight: 166,
        show_comments: false,
        auto_play: false,
      });
    }
  });
});

$(function() {
  url = window.location.href
  $(".page-share.facebook").on("click", function(e) {
    e.preventDefault();
    window.open("https://www.facebook.com/sharer/sharer.php?u="+url,
      "share", "width=600, height=400, scrollbars=no");
      ga('send', 'social', 'facebook', 'share', url);
  });

  $(".page-share.twitter").on("click", function(e) {
    e.preventDefault();
    window.open("https://twitter.com/intent/tweet?&url="+url,
      "share", "width=600, height=400, scrollbars=no");
      ga('send', 'social', 'twitter', 'share', url);
  });

  $(".page-share.linkedin").on("click", function(e) {
    e.preventDefault();
    window.open("https://www.linkedin.com/shareArticle?mini=true&source=PMG&url="+url,
      "share", "width=600, height=400, scrollbars=no");
      ga('send', 'social', 'linkedin', 'share', url);
  });

  $(".page-share.email").on("click", function(e) {
    e.preventDefault();
    var emailTitle = encodeURIComponent(document.title).replace(/&/g, '%26');
    window.location = 'mailto:?subject=' + emailTitle + '&body=I saw this on pmg.org.za and thought it might interest you: ' + url;
    ga('send', 'social', 'email', 'share', url);
  });
});

$(".committee-attendance-overview .centre-line").each(function() {
  $(this).height($(this).parent().height() + 17);
});

var displayTime = 8000,
    transitionTime = 500;
var currIndex = 0;
var $features = $(".home-banner .single-feature");
var featuresLength = $features.length;

function featuresSlide() {
  currIndex = (currIndex < (featuresLength - 1)) ? currIndex + 1 : 0;
  setTimeout(function() {
    $features.css('z-index', 1);
    $features.eq(currIndex).css('z-index', 2).fadeIn(transitionTime, function() {
      $features.not(this).hide();
      featuresSlide();
    });
  }, displayTime);
}

featuresSlide();

$(function(){
    $('#correctPageForm').on('submit', function(event){
	event.preventDefault();
	$.ajax({
	    url: '/correct-this-page',
	    method: 'POST',
	    data: $('#correctPageForm').serialize(),
	    success: function(data){
		if (data.status == 'Ok'){
		    console.log('Message has been sent');
		    $('#successForm').text("Message has been sent");
		}
		else{
		    console.log("Unable to send message");
		    console.log(data.errors);
		    $('#errorForm').text(data.errors);
		    
		}
	    },
	    error: function(data){
		console.log('Unable to sent Message');
	    }
	});
    });
});
