$(function() {
  $('.blog-page .list-group-item').on('click', function() {
    $('.fa', this)
      .toggleClass('fa-chevron-up')
      .toggleClass('fa-chevron-down')
  });
});

