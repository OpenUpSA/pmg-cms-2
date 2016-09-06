var $search = $('#committee-search');
var $searchInput = $('#committee-search input');

$('#committee-nav a').on('click', function (e) {
  e.preventDefault();
  $(this).tab('show');
});

$searchInput.on('focus', function() {
  $(document).on('keypress', function(e) {
    if(e.which === 13) {
      if($searchInput.val().length > 0) {
        $search.removeClass('has-error');
      } else {
        $search.addClass('has-error');
      }
    }
  });
});

$searchInput.on('blur', function() {
  $(document).off('keypress');
})
