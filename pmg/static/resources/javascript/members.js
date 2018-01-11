$(function() {
  var $form = $('#member-search-form'),
      $q = $form.find('[name=q]'),
      lastSearch = '',
      $members = $('.mp-list .single-member');

  var memberSearch = function(q) {
    q = q.trim().toLowerCase();
    if (lastSearch == q) return;

    lastSearch = q;

    if (!q) {
      $members.show();
    } else {
      var $matches = $('.mp-list .single-member').filter(function() {
        var $li = $(this);
        return (
          ($li.find('.name').text().toLowerCase().indexOf(q) >= 0) ||
          ($li.find('.party').text().toLowerCase().indexOf(q) >= 0) ||
          ($li.find('.province').text().toLowerCase().indexOf(q) >= 0)
        );
      });

      $members.hide();
      $matches.show();
    }
  };

  $form.on('submit', function(e) {
    e.preventDefault();
    memberSearch($q.val());
  });

  $q.on('keyup', function(e) {
    memberSearch($q.val());
  });
});

$("#member-search-form input.form-control").bind("change keyup mouseout", function () {
  if ( $("#member-search-form input.form-control").val().length > 0 ) {
    $(".show-all").hide();
    $(".mp-list").addClass("searching");
  } else {
    $(".show-all").show();
    $(".mp-list").removeClass("searching");
  }
})

$(".show-all").click(function(e) {
  e.preventDefault();
  $(this).prev(".mp-list").removeClass("collapsed");
  $(this).remove();
});

$(".mp-list").each(function(){
  if ( $(this).height() < 250 ) {
    $(this).next(".show-all").remove();
  }
});