$(function() {
  var AlertForm = function() {
    var self = this;

    self.init = function() {
      self.form = $('#new_alert_form');
      self.form.on('submit', function(e) {
        if (self.form.find('[name=previewed]').val() == "0") {
          e.preventDefault();
          self.preview();
        }
      });
      $('.btn.send').on('click', self.send);

      $('input.check-all').on('change', self.toggleAllCommittees);

      self.editor = CKEDITOR.replace('body');
    };

    self.toggleAllCommittees = function(e) {
      var checked = $(this).prop('checked');
      $(this).parents('.committee-group').find('[name=committee_ids]').prop('checked', checked);
    },

    self.preview = function() {
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
          self.form.find('[name=previewed]').val('-1');
          self.form.submit();
        });
    };

    self.send = function() {
      $('.btn.send').prop('disabled', true).text('Sending');

      self.form.find('[name=previewed]').val('1');
      self.form.submit();
    };
  };

  if ($('#new_alert_form').length > 0) {
    window.alertForm = new AlertForm();
    window.alertForm.init();
  }
});
