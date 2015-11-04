$(function() {
  if ($('body').hasClass('email_alerts')) {
    // disable checkboxes when not logged in
    $('body.not-logged-in input[type=checkbox]').prop('disabled', true);

    // set select-all value on page load
    $(".select-all").each(function(){
      var select_all = $(this);
      var all_checked = true;
      var parent_list = select_all.closest('ul');
      parent_list.find(':checkbox.select-committee').each(function(){
        var tmp_checkbox = $(this);
        if(!tmp_checkbox.is(':checked'))
        {
          all_checked = false;
          return false; // break out of 'each' loop
        }
      });
      if(all_checked)
        select_all.prop("checked", true);
    });

    // toggle list of checkboxes with select-all
    $(".select-all").each(function(){
      var select_all = $(this);
      select_all.on('change', function(){
        var parent_list = select_all.closest('ul');
        if (select_all.is(':checked'))
        {
          // check all other boxes in the list
          parent_list.find(':checkbox.select-committee').prop('checked', true);
        }
        else
        {
          // un-check all other boxes in the list
          parent_list.find(':checkbox.select-committee').prop('checked', false);
        }
      });
    });

    $("input").on('change', function(){
      var input = $(this),
          checked = input.prop('checked');

      if (input.prop('id') === 'select-daily-schedule' ) {
        $('form#email-alerts #select-daily-schedule').prop('checked', checked);
      }
        if (input.hasClass('select-all')) {
          input.closest('.checkbox').siblings('.checkbox').find('.status-indicator').addClass('hidden');
        }
        else
        {
          input.siblings('.status-indicator').addClass('hidden');
        }


      $.post(
        '/email-alerts/',
        $( "#email-alerts" ).serialize()
      ).done(function(resp) {
        if (input.hasClass('select-all')) {
          input.closest('.checkbox').siblings('.checkbox').find('.status-indicator').removeClass('hidden');
        }
        else
        {
          input.siblings('.status-indicator').removeClass('hidden');
        }

      });
    });

    $(".remove-search-alert").on("click", function(e) {

      var btn = $(this),
          id = btn.data('id') || "",
          group = btn.closest('.grouped-search-alerts');

      $.post(
        '/user/saved-search/' + id + '/delete'
      ).done(function(resp) {
        btn.parents('.search-alert').remove();
        if (group.children('.search-alert').length === 0) {
          group.remove();
        }
        ga('send', 'event', 'user', 'remove-search-alert');
      });
    });
  }
});
