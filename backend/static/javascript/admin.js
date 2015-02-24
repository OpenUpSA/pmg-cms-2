$(function() {
  $('.custom-ckeditor').each(function() {
    CKEDITOR.replace(this, {
      extraPlugins: 'autogrow',
      height: 200,
      autoGrow_minHeight: 200,
      autoGrow_maxHeight: 600,
    });
  });
});
