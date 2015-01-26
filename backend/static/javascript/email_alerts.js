$(function() {
  var AlertForm = function() {
    var self = this;

    self.init = function() {
      self.form = $('#new_alert_form');
      self.form.find('.btn.preview').on('click', self.preview);
      $('.btn.send').on('click', self.send);

      self.editor = CKEDITOR.replace('body');
    };

    self.preview = function(e) {
      e.preventDefault();

      $('.btn.preview').prop('disabled', true);

      self.editor.updateElement();

      $.post('/admin/alerts/preview', self.form.serialize())
        .then(function(resp) {
          // show the preview
          $('#previewModal .preview-area').html(resp);
          $('#previewModal').modal();

          $('.btn.preview').prop('disabled', false);
        })
        .fail(function() {
          // validation failed, submit the form normally to get errors
          self.form.submit();
        });
    };

    self.send = function() {
      $('.btn.send').prop('disabled', true).text('Sending');

      self.form.find('[name=previewed]').val('1');
      self.form.submit();
    };
  };

  window.alertForm = new AlertForm();
  window.alertForm.init();
});
