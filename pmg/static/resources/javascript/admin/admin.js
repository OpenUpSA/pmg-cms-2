$(function() {
  $('.pmg_ckeditor').each(function() {
    CKEDITOR.replace(this, {
      extraPlugins: 'autogrow',
      height: 200,
      autoGrow_minHeight: 200,
      autoGrow_maxHeight: 600,
      disallowedContent: 'a[!name]',
      allowedContent: true,
      versionCheck: false
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

$(function() {
  $('#events').on('click', '.help-event-title', function(e) {
    e.preventDefault();
    $(this).children('i').toggleClass('fa-chevron-right');
    $(this).children('i').toggleClass('fa-chevron-down');
    $(this).siblings('.help-event-title-content').toggleClass('active');
  });
});
