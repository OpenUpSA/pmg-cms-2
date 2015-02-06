$(function() {
  var $form = $('#member-search-form'),
      $q = $form.find('[name=q]'),
      lastSearch = '',
      $members = $('.member-list li');

  var memberSearch = function(q) {
    q = q.trim().toLowerCase();
    if (lastSearch == q) return;

    lastSearch = q;

    if (!q) {
      $members.show();
    } else {
      var $matches = $('.member-list li').filter(function() {
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

