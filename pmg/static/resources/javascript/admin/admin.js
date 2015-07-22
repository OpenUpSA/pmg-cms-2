$(function() {
  $('.ckeditor').each(function() {
    CKEDITOR.replace(this, {
      extraPlugins: 'autogrow',
      height: 200,
      autoGrow_minHeight: 200,
      autoGrow_maxHeight: 600,
    });
  });
});

$(function() {
  $('.upload-answer-file').on('click', function(e) {
    e.preventDefault();
    // prompt the user to choose a file
    $('.upload-answer-form [name=file]').click();
  });

  $('.upload-answer-form [name=file]').on('change', function(e) {
    if (this.files.length > 0) {
      $('.upload-answer-file').prop('disabled', true).text('Uploading...');
      this.form.submit();
    }
  });
});
